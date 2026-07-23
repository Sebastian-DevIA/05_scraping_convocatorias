"""Tests del conector Banco Mundial (World Bank Procurement Notices).

Sin red: el transporte httpx se mockea con pytest-httpx (`httpx_mock`).
La fixture `procnotices_page1.json` es una CAPTURA REAL de la API del Banco
Mundial (`search.worldbank.org/api/v2/procnotices`) tomada el 2026-07-23 (los 5
avisos más recientes por `noticedate`). Contiene SOLO la lista `procnotices` del
objeto de respuesta. Nada de payloads inventados: los casos borde (campo
ausente, sin id/url, fecha imparseable) se ejercitan removiendo/alterando campos
de copias de registros reales, no fabricando datos.
"""

from __future__ import annotations

import copy
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.connectors.base import SourceUnavailableError
from app.connectors.worldbank import API_URL, WorldBankConnector

FIXTURE = (
    Path(__file__).resolve().parent.parent
    / "fixtures"
    / "worldbank"
    / "procnotices_page1.json"
)


@pytest.fixture()
def registros() -> list[dict]:
    """Avisos REALES capturados de la API del Banco Mundial (lista `procnotices`)."""
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _respuesta(procnotices: list[dict]) -> dict:
    """Envuelve una lista de avisos en la forma real de la respuesta de la API."""
    return {
        "rows": len(procnotices),
        "os": "0",
        "page": "1",
        "total": "412480",
        "procnotices": procnotices,
    }


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    """Elimina las pausas (rate-limit del HttpClient y backoff de tenacity)."""
    monkeypatch.setattr(time, "sleep", lambda *_a, **_k: None)


@pytest.fixture()
def conn() -> WorldBankConnector:
    return WorldBankConnector()


# --- Registro / metadata ----------------------------------------------------
def test_codigo_y_nombre(conn: WorldBankConnector) -> None:
    assert conn.codigo == "worldbank"
    assert conn.nombre == "Banco Mundial (World Bank)"


# --- Mapeo de un registro real ---------------------------------------------
def test_mapeo_registro_real(conn, registros, httpx_mock) -> None:
    httpx_mock.add_response(json=_respuesta(registros))  # 5 < PAGE_SIZE -> 1 página

    items = conn.fetch({"rate_limit_seconds": 0})

    assert len(items) == len(registros) == 5
    item = items[0]
    reg = registros[0]

    assert item.id_externo == "OP00458210"
    assert item.titulo == "SOFTWARE UPGRADE AND MAINTENANCE SERVICE PROCUREMENT"
    # notice_text es HTML: se normaliza whitespace pero conserva contenido real.
    assert item.descripcion and "Contract Award" in item.descripcion
    assert item.entidad == (
        "Seismic Resilience and Energy Efficiency in Public Buildings Project"
    )
    # "Contract Award" -> contiene "contract" -> licitacion.
    assert item.tipo == "licitacion"
    assert item.estado_fuente == "Published"
    assert item.modalidad == "Direct Selection"
    # El listado no expone monto/moneda fiables ni ubicación fina -> None.
    assert item.monto is None
    assert item.moneda is None
    assert item.departamento is None
    assert item.ciudad is None
    assert item.pais == "Turkiye"
    assert item.fecha_publicacion == datetime(2026, 7, 22, tzinfo=timezone.utc)
    assert item.fecha_publicacion.tzinfo is not None  # UTC-aware
    assert item.fecha_apertura is None
    assert item.fecha_cierre == datetime(2026, 7, 22, tzinfo=timezone.utc)
    assert item.fecha_cierre.tzinfo is not None  # UTC-aware
    assert item.requisitos is None
    assert item.url_original == (
        "https://projects.worldbank.org/en/projects-operations/"
        "procurement-detail/OP00458210"
    )
    # raw = registro íntegro para auditoría.
    assert item.raw == reg


def test_mapeo_tipo_eoi_real(conn, registros, httpx_mock) -> None:
    # OP00458234 es "Request for Expression of Interest" -> eoi.
    httpx_mock.add_response(json=_respuesta(registros))
    items = conn.fetch({})
    por_id = {i.id_externo: i for i in items}
    assert por_id["OP00458234"].tipo == "eoi"
    assert por_id["OP00458255"].tipo == "eoi"


# --- Campos ausentes / imparseables -> None --------------------------------
def test_campos_ausentes_o_imparseables_a_none(conn, registros, httpx_mock) -> None:
    reg = copy.deepcopy(registros[0])
    # Simula ausencia real de campos (dato ausente en la fuente -> None).
    for campo in (
        "notice_text",
        "procurement_method_name",
        "project_name",
        "submission_date",
        "project_ctry_name",
    ):
        reg.pop(campo, None)
    # Fecha imparseable -> None (nunca se inventa una fecha).
    reg["noticedate"] = "no-es-fecha"

    httpx_mock.add_response(json=_respuesta([reg]))
    items = conn.fetch({})

    assert len(items) == 1
    item = items[0]
    assert item.descripcion is None
    assert item.modalidad is None
    assert item.entidad is None
    assert item.fecha_cierre is None
    assert item.fecha_publicacion is None
    # project_ctry_name ausente -> fallback "Global" (no se inventa un país real).
    assert item.pais == "Global"
    # Sigue teniendo lo obligatorio.
    assert item.id_externo == "OP00458210"
    assert item.titulo  # bid_description sigue presente
    assert item.url_original


def test_titulo_fallback_a_project_name(conn, registros, httpx_mock) -> None:
    reg = copy.deepcopy(registros[0])
    reg.pop("bid_description", None)  # sin bid_description -> usa project_name
    httpx_mock.add_response(json=_respuesta([reg]))
    items = conn.fetch({})
    assert len(items) == 1
    assert items[0].titulo == reg["project_name"]


# --- Registro sin id (sin URL construible) -> descartado -------------------
def test_registro_sin_id_se_descarta(conn, registros, httpx_mock) -> None:
    sin_id = copy.deepcopy(registros[0])
    sin_id.pop("id", None)  # sin id no hay url_original -> se descarta
    con_id = registros[1]

    httpx_mock.add_response(json=_respuesta([sin_id, con_id]))
    items = conn.fetch({})

    # Solo sobrevive el que tiene id (y por tanto URL).
    assert len(items) == 1
    assert items[0].id_externo == con_id["id"]


def test_registro_sin_titulo_se_descarta(conn, registros, httpx_mock) -> None:
    reg = copy.deepcopy(registros[0])
    reg.pop("bid_description", None)
    reg.pop("project_name", None)  # sin ningún título -> descartado
    httpx_mock.add_response(json=_respuesta([reg]))
    items = conn.fetch({})
    assert items == []


# --- Paginación (2 páginas) ------------------------------------------------
def test_paginacion_dos_paginas(conn, registros, httpx_mock) -> None:
    conn.PAGE_SIZE = 3  # con 5 avisos reales -> pág1=3 (llena) + pág2=2 (parcial)
    httpx_mock.add_response(json=_respuesta(registros[:3]))
    httpx_mock.add_response(json=_respuesta(registros[3:]))

    items = conn.fetch({"max_paginas": 5})

    assert len(items) == 5
    requests = httpx_mock.get_requests()
    assert len(requests) == 2
    # Offsets incrementales y tamaño de página correctos.
    assert requests[0].url.params.get("os") == "0"
    assert requests[0].url.params.get("rows") == "3"
    assert requests[1].url.params.get("os") == "3"
    # Se golpea el endpoint real de la API.
    assert str(requests[0].url).startswith(API_URL)
    # Los parámetros esperados viajan en cada request.
    assert requests[0].url.params.get("format") == "json"
    assert requests[0].url.params.get("srt") == "noticedate"


def test_max_paginas_topa_la_paginacion(conn, registros, httpx_mock) -> None:
    conn.PAGE_SIZE = 5  # cada página "llena" -> intentaría seguir paginando
    # Con max_paginas=2 solo debe hacer 2 requests aunque siempre venga página llena.
    httpx_mock.add_response(json=_respuesta(registros), is_reusable=True)

    conn.fetch({"max_paginas": 2})

    assert len(httpx_mock.get_requests()) == 2


# --- Errores: 5xx agotando reintentos --------------------------------------
def test_5xx_agota_reintentos_source_unavailable(conn, httpx_mock) -> None:
    httpx_mock.add_response(status_code=503, is_reusable=True)

    with pytest.raises(SourceUnavailableError):
        conn.fetch({"rate_limit_seconds": 0})

    # HttpClient reintenta hasta 3 intentos antes de rendirse.
    assert len(httpx_mock.get_requests()) == 3
