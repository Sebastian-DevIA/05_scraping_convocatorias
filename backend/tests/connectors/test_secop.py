"""Tests del conector SECOP II.

Sin red: el transporte httpx se mockea con pytest-httpx (`httpx_mock`).
La fixture `page1_tecnologia_2026.json` es una CAPTURA REAL de la API Socrata
(`datos.gov.co`, dataset p6dx-8zbt) tomada el 2026-07-23 con la MISMA query que
construye el conector::

    $where = fecha_de_publicacion_del > '2026-07-20T00:00:00'
             AND adjudicado='No'
             AND ((lower(nombre_del_procedimiento) like '%tecnolog%'
                   OR lower(descripci_n_del_procedimiento) like '%tecnolog%'))
    $order = fecha_de_publicacion_del ASC, id_del_proceso ASC
    $limit = 12

Esos 12 registros traen de forma NATURAL los dos casos de `fecha_de_recepcion_de`
(3 lo tienen — modalidad "Mínima cuantía" —, 9 no: Socrata omite el campo nulo)
y los dos valores de `ordenentidad` más frecuentes ('Territorial' y 'Nacional').
Nada de payloads inventados: los casos borde (campo ausente, sin URL) se
ejercitan removiendo campos de copias de registros reales, no fabricando datos.
"""

from __future__ import annotations

import copy
import json
import re
import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from app.connectors.base import SourceUnavailableError
from app.connectors.secop import DATASET_URL, SecopConnector

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "secop" / "page1_tecnologia_2026.json"


@pytest.fixture()
def registros() -> list[dict]:
    """Registros REALES capturados de la API SECOP II."""
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    """Elimina las pausas (rate-limit del HttpClient y backoff de tenacity)."""
    monkeypatch.setattr(time, "sleep", lambda *_a, **_k: None)


@pytest.fixture()
def conn() -> SecopConnector:
    return SecopConnector()


# --- Registro / metadata ----------------------------------------------------
def test_codigo_y_nombre(conn: SecopConnector) -> None:
    assert conn.codigo == "secop"
    assert conn.nombre


# --- Mapeo de un registro real ---------------------------------------------
def test_mapeo_registro_real(conn, registros, httpx_mock) -> None:
    httpx_mock.add_response(json=registros)  # una sola página (12 < PAGE_SIZE)

    items = conn.fetch({"keywords": ["tecnolog"], "rate_limit_seconds": 0})

    assert len(items) == len(registros) == 12
    item = items[0]
    reg = registros[0]

    assert item.id_externo == "CO1.REQ.10602402"
    assert item.titulo.startswith("PRESTACIÓN DE SERVICIOS DE APOYO A LA GESTIÓN")
    assert item.descripcion and "TECNOLOGÍAS DE LA INFORMACIÓN" in item.descripcion
    assert item.entidad == "ASAMBLEA DEPARTAMENTAL DE ANTIOQUIA"
    assert item.tipo == "licitacion"
    assert item.estado_fuente == "Publicado"
    assert item.modalidad == "Contratación directa"
    assert item.monto == Decimal("16000000")
    assert item.moneda == "COP"
    assert item.departamento == "Antioquia"
    assert item.ciudad == "Medellín"
    assert item.pais == "Colombia"
    # Ámbito CRUDO tal cual lo reporta la fuente (`ordenentidad`): el conector
    # NO mapea al ámbito canónico, eso es del pipeline.
    assert item.ambito_fuente == "Territorial"
    assert item.fecha_publicacion == datetime(2026, 7, 21, tzinfo=timezone.utc)
    assert item.fecha_publicacion.tzinfo is not None  # UTC-aware
    # Contratación directa: el registro real no trae `fecha_de_recepcion_de`.
    assert "fecha_de_recepcion_de" not in reg
    assert item.fecha_cierre is None
    # El dataset no expone apertura ni requisitos -> None (no se inventan).
    assert item.fecha_apertura is None
    assert item.requisitos is None
    assert item.url_original == (
        "https://community.secop.gov.co/Public/Tendering/"
        "OpportunityDetail/Index?noticeUID=CO1.NTC.10546231"
    )
    # raw = registro íntegro para auditoría.
    assert item.raw == reg


# --- Ámbito crudo (`ordenentidad`) -----------------------------------------
def test_ambito_fuente_crudo_de_ordenentidad(conn, registros, httpx_mock) -> None:
    httpx_mock.add_response(json=registros)
    items = conn.fetch({"keywords": ["tecnolog"]})

    ambitos = {item.ambito_fuente for item in items}
    # Valores REALES del dataset presentes en la captura, sin mapear.
    assert ambitos == {"Territorial", "Nacional"}
    # Cada item conserva exactamente el `ordenentidad` de su registro.
    for item, reg in zip(items, registros, strict=True):
        assert item.ambito_fuente == reg["ordenentidad"]


def test_ambito_fuente_none_si_falta_ordenentidad(conn, registros, httpx_mock) -> None:
    reg = copy.deepcopy(registros[0])
    reg.pop("ordenentidad", None)  # dato ausente en la fuente -> None
    httpx_mock.add_response(json=[reg])
    items = conn.fetch({"keywords": ["tecnolog"]})
    assert items[0].ambito_fuente is None


# --- Cierre de recepción de ofertas (`fecha_de_recepcion_de`) --------------
def test_fecha_cierre_parseada_de_fecha_de_recepcion(conn, registros, httpx_mock) -> None:
    httpx_mock.add_response(json=registros)
    items = conn.fetch({"keywords": ["tecnolog"]})

    # Registro real de "Mínima cuantía" que SÍ trae el deadline de ofertas.
    con_cierre = next(i for i in items if i.id_externo == "CO1.REQ.10650033")
    assert con_cierre.fecha_cierre == datetime(2026, 7, 27, tzinfo=timezone.utc)
    assert con_cierre.fecha_cierre.tzinfo is not None  # UTC-aware

    # El resto de la captura real: cierre solo donde la fuente lo publica.
    esperados = {
        reg["id_del_proceso"]: reg.get("fecha_de_recepcion_de") for reg in registros
    }
    for item in items:
        if esperados[item.id_externo] is None:
            assert item.fecha_cierre is None
        else:
            assert item.fecha_cierre is not None


def test_fecha_cierre_none_si_falta_el_campo(conn, registros, httpx_mock) -> None:
    """Socrata omite `fecha_de_recepcion_de` cuando es nulo -> fecha_cierre None."""
    con_cierre = next(r for r in registros if "fecha_de_recepcion_de" in r)
    reg = copy.deepcopy(con_cierre)
    reg.pop("fecha_de_recepcion_de")

    httpx_mock.add_response(json=[reg])
    items = conn.fetch({"keywords": ["tecnolog"]})

    assert len(items) == 1  # no rompe el mapeo
    assert items[0].fecha_cierre is None


def test_fecha_cierre_imparseable_a_none(conn, registros, httpx_mock) -> None:
    con_cierre = next(r for r in registros if "fecha_de_recepcion_de" in r)
    reg = copy.deepcopy(con_cierre)
    reg["fecha_de_recepcion_de"] = "no-es-fecha"

    httpx_mock.add_response(json=[reg])
    items = conn.fetch({"keywords": ["tecnolog"]})

    # Nunca se inventa una fecha: imparseable -> None.
    assert items[0].fecha_cierre is None


def test_monto_es_decimal_o_none(conn, registros, httpx_mock) -> None:
    httpx_mock.add_response(json=registros)
    items = conn.fetch({"keywords": ["tecnolog"]})
    for item in items:
        assert item.monto is None or isinstance(item.monto, Decimal)


# --- Campos ausentes / imparseables -> None --------------------------------
def test_campos_ausentes_o_imparseables_a_none(conn, registros, httpx_mock) -> None:
    reg = copy.deepcopy(registros[0])
    # Simula ausencia real de campos (dato ausente en la fuente -> None).
    for campo in (
        "precio_base",
        "departamento_entidad",
        "ciudad_entidad",
        "modalidad_de_contratacion",
        "descripci_n_del_procedimiento",
    ):
        reg.pop(campo, None)
    # Fecha imparseable -> None (nunca se inventa una fecha).
    reg["fecha_de_publicacion_del"] = "no-es-fecha"

    httpx_mock.add_response(json=[reg])
    items = conn.fetch({"keywords": ["tecnolog"]})

    assert len(items) == 1
    item = items[0]
    assert item.monto is None
    assert item.departamento is None
    assert item.ciudad is None
    assert item.modalidad is None
    assert item.descripcion is None
    assert item.fecha_publicacion is None
    # Sigue teniendo lo obligatorio.
    assert item.id_externo == "CO1.REQ.10602402"
    assert item.url_original


def test_precio_vacio_a_none(conn, registros, httpx_mock) -> None:
    reg = copy.deepcopy(registros[0])
    reg["precio_base"] = ""
    httpx_mock.add_response(json=[reg])
    items = conn.fetch({"keywords": ["tecnolog"]})
    assert items[0].monto is None


# --- Registro sin URL -> descartado ----------------------------------------
def test_registro_sin_url_se_descarta(conn, registros, httpx_mock) -> None:
    sin_url = copy.deepcopy(registros[0])
    sin_url.pop("urlproceso", None)  # sin url_original obligatoria
    con_url = registros[1]

    httpx_mock.add_response(json=[sin_url, con_url])
    items = conn.fetch({"keywords": ["tecnolog"]})

    # Solo sobrevive el que tiene URL.
    assert len(items) == 1
    assert items[0].id_externo == con_url["id_del_proceso"]


def test_urlproceso_sin_clave_url_se_descarta(conn, registros, httpx_mock) -> None:
    reg = copy.deepcopy(registros[0])
    reg["urlproceso"] = {}  # dict sin "url"
    httpx_mock.add_response(json=[reg])
    items = conn.fetch({"keywords": ["tecnolog"]})
    assert items == []


# --- Paginación (2 páginas) ------------------------------------------------
def test_paginacion_dos_paginas(conn, registros, httpx_mock) -> None:
    conn.PAGE_SIZE = 8  # con 12 registros reales -> pág1=8 (llena) + pág2=4 (parcial)
    pagina1 = registros[:8]
    pagina2 = registros[8:]
    httpx_mock.add_response(json=pagina1)
    httpx_mock.add_response(json=pagina2)

    items = conn.fetch({"keywords": ["tecnolog"], "max_paginas": 5})

    assert len(items) == 12
    requests = httpx_mock.get_requests()
    assert len(requests) == 2
    # Offsets incrementales y tamaño de página correctos.
    assert requests[0].url.params.get("$offset") == "0"
    assert requests[0].url.params.get("$limit") == "8"
    assert requests[1].url.params.get("$offset") == "8"
    # Se golpea el endpoint real del dataset.
    assert str(requests[0].url).startswith(DATASET_URL)
    # El $where viaja en cada request.
    assert "fecha_de_publicacion_del" in requests[0].url.params.get("$where")
    assert requests[0].url.params.get("$order") == "fecha_de_publicacion_del ASC, id_del_proceso ASC"


def test_max_paginas_topa_la_paginacion(conn, registros, httpx_mock) -> None:
    conn.PAGE_SIZE = 12  # cada página "llena" -> intentaría seguir paginando
    # Con max_paginas=2 solo debe hacer 2 requests aunque siempre venga página llena.
    httpx_mock.add_response(json=registros, is_reusable=True)

    conn.fetch({"keywords": ["tecnolog"], "max_paginas": 2})

    assert len(httpx_mock.get_requests()) == 2


# --- Errores: 5xx agotando reintentos --------------------------------------
def test_5xx_agota_reintentos_source_unavailable(conn, httpx_mock) -> None:
    httpx_mock.add_response(status_code=503, is_reusable=True)

    with pytest.raises(SourceUnavailableError):
        conn.fetch({"keywords": ["tecnolog"], "rate_limit_seconds": 0})

    # HttpClient reintenta hasta 3 intentos antes de rendirse.
    assert len(httpx_mock.get_requests()) == 3


# --- Construcción del $where -----------------------------------------------
def test_where_incluye_fecha_desde_estado_y_keywords(conn) -> None:
    where = conn._build_where(
        {"fecha_desde": "2026-06-01T00:00:00", "keywords": ["Tecnología", "TIC"]}
    )
    assert "fecha_de_publicacion_del > '2026-06-01T00:00:00'" in where
    assert "adjudicado='No'" in where
    # Keywords en minúscula, OR sobre nombre y descripción.
    assert "lower(nombre_del_procedimiento) like '%tecnología%'" in where
    assert "lower(descripci_n_del_procedimiento) like '%tecnología%'" in where
    assert "lower(nombre_del_procedimiento) like '%tic%'" in where
    assert " AND " in where and " OR " in where


def test_where_default_ultimos_60_dias_si_no_hay_fecha_desde(conn) -> None:
    where = conn._build_where({"keywords": ["x"]})
    m = re.search(r"fecha_de_publicacion_del > '([^']+)'", where)
    assert m
    fecha = datetime.fromisoformat(m.group(1)).replace(tzinfo=timezone.utc)
    esperado = datetime.now(timezone.utc) - timedelta(days=60)
    # Tolerancia amplia (segundos de ejecución).
    assert abs((fecha - esperado).total_seconds()) < 120


def test_where_acepta_fecha_desde_datetime(conn) -> None:
    dt = datetime(2026, 5, 10, 12, 30, tzinfo=timezone.utc)
    where = conn._build_where({"fecha_desde": dt, "keywords": ["x"]})
    assert "fecha_de_publicacion_del > '2026-05-10T12:30:00'" in where


def test_where_fecha_desde_imparseable_cae_a_default(conn) -> None:
    where = conn._build_where({"fecha_desde": "basura", "keywords": ["x"]})
    m = re.search(r"fecha_de_publicacion_del > '([^']+)'", where)
    fecha = datetime.fromisoformat(m.group(1)).replace(tzinfo=timezone.utc)
    esperado = datetime.now(timezone.utc) - timedelta(days=60)
    assert abs((fecha - esperado).total_seconds()) < 120


def test_keyword_escapa_comilla_simple(conn) -> None:
    clause = conn._keyword_clause(["O'Brien"])
    assert clause is not None
    assert "%o''brien%" in clause  # comilla simple escapada (doblada)


def test_keyword_clause_vacia_es_none(conn) -> None:
    assert conn._keyword_clause([]) is None
    assert conn._keyword_clause(["   ", None]) is None  # type: ignore[list-item]
