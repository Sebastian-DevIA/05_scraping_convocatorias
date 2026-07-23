"""Tests del conector Grants.gov (API JSON `search2`, POST).

Sin red: el transporte httpx se mockea con pytest-httpx (`httpx_mock`).
La fixture `search2_community.json` es una CAPTURA REAL de la API Grants.gov
(`api.grants.gov/v1/api/search2`, POST keyword="community", oppStatuses="posted")
tomada el 2026-07-23. Se guardó la RESPUESTA ÍNTEGRA (envelope
`{"errorcode","data":{"hitCount","oppHits":[...]}}`). Nada de payloads inventados:
los casos borde (campo ausente, fecha imparseable, sin id/título) se ejercitan
removiendo/alterando campos de copias de `oppHits` reales, no fabricando datos.
"""

from __future__ import annotations

import copy
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.connectors.base import ParseError, SourceUnavailableError
from app.connectors.grantsgov import SEARCH_URL, GrantsGovConnector

FIXTURE = (
    Path(__file__).resolve().parent.parent
    / "fixtures"
    / "grantsgov"
    / "search2_community.json"
)


@pytest.fixture()
def respuesta() -> dict:
    """Respuesta REAL íntegra capturada de la API Grants.gov."""
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


@pytest.fixture()
def hits(respuesta) -> list[dict]:
    """Los `oppHits` reales de la captura."""
    return respuesta["data"]["oppHits"]


def _envelope(oppHits: list[dict]) -> dict:
    """Envuelve una lista de oppHits en el envelope mínimo del search2.

    Espeja la estructura real de la API para armar páginas/casos borde a partir
    de registros reales (no inventa la forma de la respuesta).
    """
    return {"errorcode": 0, "msg": "Webservice Succeeds", "data": {"hitCount": len(oppHits), "oppHits": oppHits}}


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    """Elimina las pausas (rate-limit del HttpClient y backoff de tenacity)."""
    monkeypatch.setattr(time, "sleep", lambda *_a, **_k: None)


@pytest.fixture()
def conn() -> GrantsGovConnector:
    return GrantsGovConnector()


# --- Registro / metadata ----------------------------------------------------
def test_codigo_y_nombre(conn: GrantsGovConnector) -> None:
    assert conn.codigo == "grantsgov"
    assert conn.nombre == "Grants.gov (EE. UU.)"


# --- Mapeo de un registro real ---------------------------------------------
def test_mapeo_registro_real(conn, respuesta, hits, httpx_mock) -> None:
    httpx_mock.add_response(json=respuesta)  # una sola página (5 < PAGE_SIZE)

    items = conn.fetch({"keywords": ["community"], "rate_limit_seconds": 0})

    assert len(items) == len(hits) == 5
    item = items[0]
    hit = hits[0]

    assert item.id_externo == "325599"
    assert item.titulo == "U.S. Embassy Praia Ambassador&rsquo;s Special Self-Help (SSH) Program"
    assert item.entidad == "U.S. Mission to Cape Verde"
    assert item.tipo == "subvencion"
    assert item.estado_fuente == "posted"  # crudo, sin mapear a canónico
    assert item.pais == "Estados Unidos"
    # openDate "03/19/2020" -> UTC-aware a medianoche.
    assert item.fecha_publicacion == datetime(2020, 3, 19, tzinfo=timezone.utc)
    assert item.fecha_publicacion.tzinfo is not None
    # closeDate viene "" en este registro real -> None (no se inventa).
    assert item.fecha_cierre is None
    # url_original construida con el id (patrón confirmado en vivo).
    assert item.url_original == "https://www.grants.gov/search-results-detail/325599"
    # El listado no expone estos campos -> None (no se inventan).
    assert item.descripcion is None
    assert item.modalidad is None
    assert item.monto is None
    assert item.moneda is None
    assert item.departamento is None
    assert item.ciudad is None
    assert item.fecha_apertura is None
    assert item.requisitos is None
    # raw = oppHit íntegro para auditoría.
    assert item.raw == hit


def test_close_date_presente_se_parsea(conn, hits, httpx_mock) -> None:
    httpx_mock.add_response(json=_envelope(hits))
    items = conn.fetch({"keywords": ["community"]})
    # hits[1] (id 363048) trae closeDate "08/17/2026".
    item = items[1]
    assert item.id_externo == "363048"
    assert item.fecha_publicacion == datetime(2026, 7, 2, tzinfo=timezone.utc)
    assert item.fecha_cierre == datetime(2026, 8, 17, tzinfo=timezone.utc)


# --- Campos ausentes / imparseables -> None --------------------------------
def test_campos_ausentes_o_imparseables_a_none(conn, hits, httpx_mock) -> None:
    hit = copy.deepcopy(hits[1])  # tiene ambas fechas pobladas
    hit.pop("agency", None)  # fuerza fallback a agencyCode
    hit["openDate"] = "no-es-fecha"  # fecha imparseable -> None
    hit["closeDate"] = ""  # fecha ausente -> None

    httpx_mock.add_response(json=_envelope([hit]))
    items = conn.fetch({"keywords": ["community"]})

    assert len(items) == 1
    item = items[0]
    assert item.entidad == hit["agencyCode"]  # fallback a agencyCode
    assert item.fecha_publicacion is None
    assert item.fecha_cierre is None
    # Sigue teniendo lo obligatorio.
    assert item.id_externo == "363048"
    assert item.url_original == "https://www.grants.gov/search-results-detail/363048"


def test_sin_agency_ni_agency_code_entidad_none(conn, hits, httpx_mock) -> None:
    hit = copy.deepcopy(hits[0])
    hit.pop("agency", None)
    hit.pop("agencyCode", None)
    httpx_mock.add_response(json=_envelope([hit]))
    items = conn.fetch({"keywords": ["community"]})
    assert items[0].entidad is None


# --- Registros descartados --------------------------------------------------
def test_sin_id_se_descarta(conn, hits, httpx_mock) -> None:
    sin_id = copy.deepcopy(hits[0])
    sin_id.pop("id", None)  # sin id no hay url_original construible -> descarta
    con_id = hits[1]

    httpx_mock.add_response(json=_envelope([sin_id, con_id]))
    items = conn.fetch({"keywords": ["community"]})

    assert len(items) == 1
    assert items[0].id_externo == "363048"


def test_sin_title_se_descarta(conn, hits, httpx_mock) -> None:
    hit = copy.deepcopy(hits[0])
    hit.pop("title", None)
    httpx_mock.add_response(json=_envelope([hit]))
    items = conn.fetch({"keywords": ["community"]})
    assert items == []


# --- Cuerpo POST y keywords -------------------------------------------------
def test_body_post_correcto(conn, respuesta, httpx_mock) -> None:
    httpx_mock.add_response(json=respuesta)
    conn.fetch({"keywords": ["community"], "max_paginas": 1})

    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    req = requests[0]
    assert req.method == "POST"
    assert str(req.url) == SEARCH_URL
    body = json.loads(req.read())
    assert body["keyword"] == "community"
    assert body["rows"] == conn.PAGE_SIZE
    assert body["oppStatuses"] == "posted|forecasted"
    assert body["startRecordNum"] == 0


def test_una_busqueda_por_keyword_y_dedupe(conn, respuesta, httpx_mock) -> None:
    # Dos keywords -> dos POST; ambas devuelven los mismos hits reales -> dedupe por id.
    httpx_mock.add_response(json=respuesta, is_reusable=True)

    items = conn.fetch({"keywords": ["community", "policing"]})

    requests = httpx_mock.get_requests()
    assert len(requests) == 2
    assert json.loads(requests[0].read())["keyword"] == "community"
    assert json.loads(requests[1].read())["keyword"] == "policing"
    # 5 hits repetidos en ambas búsquedas -> 5 únicos.
    assert len(items) == 5
    assert len({i.id_externo for i in items}) == 5


def test_opp_statuses_override(conn, respuesta, httpx_mock) -> None:
    httpx_mock.add_response(json=respuesta)
    conn.fetch({"keywords": ["community"], "opp_statuses": "posted"})
    body = json.loads(httpx_mock.get_requests()[0].read())
    assert body["oppStatuses"] == "posted"


def test_sin_keywords_una_busqueda_vacia(conn, respuesta, httpx_mock, monkeypatch) -> None:
    # Sin keywords en config ni settings -> una sola búsqueda con keyword="".
    # `settings.keywords` es una property computada; se sustituye el objeto
    # settings del módulo por uno falso sin keywords.
    from types import SimpleNamespace

    from app.connectors import grantsgov as mod

    monkeypatch.setattr(mod, "settings", SimpleNamespace(keywords=[]))
    httpx_mock.add_response(json=respuesta)

    conn.fetch({})

    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    assert json.loads(requests[0].read())["keyword"] == ""


# --- Paginación -------------------------------------------------------------
def test_paginacion_dos_paginas(conn, hits, httpx_mock) -> None:
    conn.PAGE_SIZE = 3  # con 5 hits reales -> pág1=3 (llena) + pág2=2 (parcial)
    httpx_mock.add_response(json=_envelope(hits[:3]))
    httpx_mock.add_response(json=_envelope(hits[3:]))

    items = conn.fetch({"keywords": ["community"], "max_paginas": 5})

    assert len(items) == 5
    requests = httpx_mock.get_requests()
    assert len(requests) == 2
    # startRecordNum incremental y rows correcto.
    assert json.loads(requests[0].read())["startRecordNum"] == 0
    assert json.loads(requests[0].read())["rows"] == 3
    assert json.loads(requests[1].read())["startRecordNum"] == 3


def test_max_paginas_topa_la_paginacion(conn, hits, httpx_mock) -> None:
    conn.PAGE_SIZE = 5  # cada página "llena" -> intentaría seguir paginando
    httpx_mock.add_response(json=_envelope(hits), is_reusable=True)

    conn.fetch({"keywords": ["community"], "max_paginas": 2})

    assert len(httpx_mock.get_requests()) == 2


# --- Errores ----------------------------------------------------------------
def test_5xx_agota_reintentos_source_unavailable(conn, httpx_mock) -> None:
    httpx_mock.add_response(status_code=503, is_reusable=True)

    with pytest.raises(SourceUnavailableError):
        conn.fetch({"keywords": ["community"], "rate_limit_seconds": 0})

    # HttpClient reintenta hasta 3 intentos antes de rendirse.
    assert len(httpx_mock.get_requests()) == 3


def test_respuesta_sin_opp_hits_parse_error(conn, httpx_mock) -> None:
    httpx_mock.add_response(json={"errorcode": 0, "data": {"hitCount": 0}})
    with pytest.raises(ParseError):
        conn.fetch({"keywords": ["community"]})


def test_respuesta_sin_data_parse_error(conn, httpx_mock) -> None:
    httpx_mock.add_response(json={"errorcode": 1, "msg": "boom"})
    with pytest.raises(ParseError):
        conn.fetch({"keywords": ["community"]})
