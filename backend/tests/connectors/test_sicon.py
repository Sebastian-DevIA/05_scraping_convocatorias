"""Tests del conector SICON (convocatorias de cultura del Distrito de Bogotá).

Sin red: el transporte httpx se mockea con pytest-httpx (`httpx_mock`).
La fixture `convocatorias_publicadas_page1.json` es una CAPTURA REAL de la API
(`sicon.scrd.gov.co`, endpoint `DrupalWS/convocatorias_publicadas`) tomada el
2026-07-23: son los registros del array `respuesta` tal cual los devolvió la
fuente (FUGA, SCRD, IDARTES...), sin edición manual. Los casos borde (campo
ausente, error de negocio) se ejercitan removiendo campos de copias de registros
reales o construyendo el sobre de error tal como lo emite la propia fuente, no
fabricando convocatorias.

El conector necesita dos peticiones: primero un GET al token público
(`cultured.gov.co/config/config.txt`) y luego el POST del listado; ambos se
mockean.
"""

from __future__ import annotations

import copy
import json
import time
from datetime import timezone
from decimal import Decimal
from pathlib import Path

import pytest

from app.connectors.base import ParseError
from app.connectors.sicon import (
    AMBITO_SICON,
    API_URL,
    CIUDAD_SICON,
    DEPARTAMENTO_SICON,
    TOKEN_URL,
    SiconConnector,
)

FIXTURE = (
    Path(__file__).resolve().parent.parent
    / "fixtures"
    / "sicon"
    / "convocatorias_publicadas_page1.json"
)

TOKEN_BODY = "TOKEN-DE-PRUEBA{{Thu Jul 23 2026 07:00:02 GMT+0000}}"


@pytest.fixture()
def registros() -> list[dict]:
    """Registros REALES capturados del array `respuesta` de la API SICON."""
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    """Elimina las pausas (rate-limit del HttpClient y backoff de tenacity)."""
    monkeypatch.setattr(time, "sleep", lambda *_a, **_k: None)


@pytest.fixture()
def conn() -> SiconConnector:
    return SiconConnector()


def _mock_token(httpx_mock, body: str = TOKEN_BODY) -> None:
    httpx_mock.add_response(url=TOKEN_URL, method="GET", text=body)


def _mock_listado(httpx_mock, registros: list[dict]) -> None:
    """Responde el POST del listado con el sobre real de la fuente."""
    httpx_mock.add_response(
        url=API_URL,
        method="POST",
        json={
            "error": 0,
            "total_registros": len(registros),
            "total_registros_sin_filtro": len(registros),
            "respuesta": registros,
        },
    )


def test_fetch_mapea_registros_reales(httpx_mock, conn, registros) -> None:
    _mock_token(httpx_mock)
    _mock_listado(httpx_mock, registros)

    items = conn.fetch({"max_paginas": 1, "rate_limit_seconds": 0})

    assert len(items) == len(registros)
    # Todos con url_original construida desde el id real y ámbito territorial crudo.
    for it, reg in zip(items, registros):
        assert it.url_original == f"https://cultured.gov.co/detalle/convocatorias/{reg['id']}"
        assert it.ambito_fuente == AMBITO_SICON  # "Territorial", sin mapear
        assert it.departamento == DEPARTAMENTO_SICON
        assert it.ciudad == CIUDAD_SICON
        assert it.pais == "Colombia"


def test_estado_fuente_va_crudo(httpx_mock, conn, registros) -> None:
    """El conector NO mapea estado: entrega el texto crudo de la fuente."""
    _mock_token(httpx_mock)
    _mock_listado(httpx_mock, registros)

    items = conn.fetch({"max_paginas": 1, "rate_limit_seconds": 0})

    estados_crudos = {reg.get("estado") for reg in registros}
    assert {it.estado_fuente for it in items} <= estados_crudos
    # En la captura conviven 'Publicada' y 'Publicada Cerrada'.
    assert any(it.estado_fuente == "Publicada" for it in items)


def test_fecha_cierre_desde_cronograma_en_utc(httpx_mock, conn, registros) -> None:
    _mock_token(httpx_mock)
    _mock_listado(httpx_mock, registros)

    items = conn.fetch({"max_paginas": 1, "rate_limit_seconds": 0})

    con_cierre = [it for it in items if it.fecha_cierre is not None]
    assert con_cierre, "la captura real trae al menos una fecha de cierre"
    for it in con_cierre:
        # Normalizada a UTC (la fuente publica en hora de Bogotá, UTC-5).
        assert it.fecha_cierre.tzinfo is not None
        assert it.fecha_cierre.utcoffset() == timezone.utc.utcoffset(None)


def test_monto_en_pesos_o_none(httpx_mock, conn, registros) -> None:
    _mock_token(httpx_mock)
    _mock_listado(httpx_mock, registros)

    items = conn.fetch({"max_paginas": 1, "rate_limit_seconds": 0})

    for it in items:
        if it.monto is not None:
            assert isinstance(it.monto, Decimal)
            assert it.monto > 0
            assert it.moneda == "COP"
        else:
            assert it.moneda is None


def test_registro_sin_id_se_descarta(httpx_mock, conn, registros) -> None:
    """Sin `id` no hay url_original construible -> se descarta (no se inventa)."""
    mutados = copy.deepcopy(registros)
    mutados[0].pop("id", None)
    _mock_token(httpx_mock)
    _mock_listado(httpx_mock, mutados)

    items = conn.fetch({"max_paginas": 1, "rate_limit_seconds": 0})

    assert len(items) == len(registros) - 1


def test_error_de_negocio_se_propaga(httpx_mock, conn) -> None:
    """`error != 0` (ej. token vencido) -> ParseError, nunca lista vacía silenciosa."""
    _mock_token(httpx_mock)
    httpx_mock.add_response(
        url=API_URL,
        method="POST",
        json={"error": 2, "respuesta": "El token no es correcto"},
    )

    with pytest.raises(ParseError):
        conn.fetch({"max_paginas": 1, "rate_limit_seconds": 0})


def test_token_vacio_es_parse_error(httpx_mock, conn) -> None:
    """Si el archivo de token no trae token, se falla tipado (no se sigue a ciegas)."""
    _mock_token(httpx_mock, body="{{solo timestamp}}")

    with pytest.raises(ParseError):
        conn.fetch({"max_paginas": 1, "rate_limit_seconds": 0})
