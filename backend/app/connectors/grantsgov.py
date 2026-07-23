"""Conector Grants.gov — subvenciones federales de EE. UU. (API JSON `search2`).

Fuente: portal oficial Grants.gov del gobierno de EE. UU. Se consulta vía POST
sobre el endpoint JSON `search2` (Search API v1).

Estrategia (verificada en vivo el 2026-07-23 contra la API real):
  - El endpoint es POST con cuerpo JSON:
        {"rows": N, "keyword": "<kw>", "oppStatuses": "posted|forecasted",
         "startRecordNum": <offset>}
    Respuesta: {"errorcode":0, "data":{"hitCount":N, "oppHits":[...], ...}}.
  - El API acepta UN solo `keyword` por request, así que se hace una búsqueda
    POST por cada keyword de ``config["keywords"]`` y se deduplica por `id`
    (una misma convocatoria puede matchear varias keywords). Si no hay keywords,
    se hace una única búsqueda con `keyword=""` (trae todo lo abierto/pronto).
  - Paginación con `startRecordNum` += `PAGE_SIZE` hasta ``config["max_paginas"]``
    páginas; se corta cuando una página trae menos de `PAGE_SIZE` registros.
  - `oppStatuses` por defecto "posted|forecasted" (abiertas y próximas);
    overridable por ``config["opp_statuses"]``.

Mapeo a `RawConvocatoria` (campos crudos reales de cada `oppHit`):
  id_externo <- id                          titulo      <- title (sin él, descarta)
  entidad    <- agency (fallback agencyCode) tipo        = "subvencion"
  estado_fuente<- oppStatus (crudo, sin mapear a canónico)
  fecha_publicacion <- openDate (MM/DD/YYYY -> UTC)
  fecha_cierre <- closeDate (MM/DD/YYYY -> UTC)
  url_original <- https://www.grants.gov/search-results-detail/{id} (OBLIGATORIA)
  raw        = oppHit íntegro

El listado NO trae descripción, monto, moneda, ubicación, fecha de apertura ni
requisitos (viven en el detalle), por eso quedan en None (nunca se inventan).
`modalidad` se deja en None: `docType` (ej. "synopsis") describe el documento,
no una modalidad de participación.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.config import settings
from app.connectors.base import BaseConnector, ParseError
from app.connectors.http import get_http_client
from app.schemas.raw import RawConvocatoria

logger = logging.getLogger(__name__)

# --- Endpoint y detalle (verificados en vivo) ------------------------------
SEARCH_URL = "https://api.grants.gov/v1/api/search2"
DETAIL_URL_TMPL = "https://www.grants.gov/search-results-detail/{id}"

# Formato de fecha real de la fuente (ej. "07/02/2026").
DATE_FMT = "%m/%d/%Y"

# --- Defaults (overridables por `config`) ----------------------------------
DEFAULT_MAX_PAGINAS = 5
DEFAULT_OPP_STATUSES = "posted|forecasted"
PAIS = "Estados Unidos"


def _txt(value: object) -> str | None:
    """Normaliza a str no vacío o None (dato ausente -> None)."""
    if value is None:
        return None
    s = str(value).strip()
    return s or None


def _parse_dt_utc(value: object) -> datetime | None:
    """Fecha `MM/DD/YYYY` de Grants.gov -> datetime UTC. Vacía/imparseable -> None.

    La fuente entrega solo la fecha (sin hora ni zona); se fija a medianoche UTC.
    """
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    try:
        dt = datetime.strptime(s, DATE_FMT)
    except ValueError:
        return None
    return dt.replace(tzinfo=timezone.utc)


class GrantsGovConnector(BaseConnector):
    """Conector de Grants.gov (API JSON `search2`, POST)."""

    codigo = "grantsgov"
    nombre = "Grants.gov (EE. UU.)"

    # Tamaño de página del search2. Constante de clase para poder ajustarla en
    # tests de paginación sin necesitar cientos de registros reales.
    PAGE_SIZE = 100

    # --- Mapeo registro -> RawConvocatoria ---------------------------------
    def _map(self, hit: dict) -> RawConvocatoria | None:
        """Mapea un `oppHit` crudo. Devuelve None si debe descartarse."""
        if not isinstance(hit, dict):
            logger.warning("Grants.gov: oppHit no es objeto JSON, descartado")
            return None

        id_externo = _txt(hit.get("id"))
        if not id_externo:
            logger.warning("Grants.gov: oppHit sin id (sin url_original), descartado")
            return None

        titulo = _txt(hit.get("title"))
        if not titulo:
            logger.warning(
                "Grants.gov: oppHit sin title (id=%s), descartado", id_externo
            )
            return None

        # url_original SIEMPRE presente: se construye con el id (patrón confirmado).
        url = DETAIL_URL_TMPL.format(id=id_externo)

        # estado_fuente es obligatorio (str); crudo, el pipeline lo mapea.
        estado = _txt(hit.get("oppStatus")) or ""

        return RawConvocatoria(
            id_externo=id_externo,
            titulo=titulo,
            # El listado no trae descripción -> None (no se inventa).
            descripcion=None,
            entidad=_txt(hit.get("agency")) or _txt(hit.get("agencyCode")),
            tipo="subvencion",
            estado_fuente=estado,
            # docType describe el documento, no una modalidad de participación.
            modalidad=None,
            monto=None,
            moneda=None,
            departamento=None,
            ciudad=None,
            pais=PAIS,
            fecha_publicacion=_parse_dt_utc(hit.get("openDate")),
            # El listado no expone fecha de apertura ni requisitos -> None.
            fecha_apertura=None,
            fecha_cierre=_parse_dt_utc(hit.get("closeDate")),
            requisitos=None,
            url_original=url,
            raw=hit,
        )

    # --- Extracción de la respuesta ----------------------------------------
    def _opp_hits(self, payload: object) -> list:
        """Valida la respuesta y devuelve la lista `data.oppHits`.

        Lanza ParseError si la estructura no es la esperada (posible cambio de API).
        """
        if not isinstance(payload, dict):
            raise ParseError(
                f"Grants.gov: se esperaba un objeto JSON, llegó {type(payload).__name__}"
            )
        data = payload.get("data")
        if not isinstance(data, dict):
            raise ParseError("Grants.gov: respuesta sin objeto 'data'")
        hits = data.get("oppHits")
        if not isinstance(hits, list):
            raise ParseError("Grants.gov: 'data.oppHits' ausente o no es lista")
        return hits

    # --- API del conector --------------------------------------------------
    def fetch(self, config: dict) -> list[RawConvocatoria]:
        config = config or {}
        try:
            max_paginas = int(config.get("max_paginas") or DEFAULT_MAX_PAGINAS)
        except (TypeError, ValueError):
            max_paginas = DEFAULT_MAX_PAGINAS
        opp_statuses = _txt(config.get("opp_statuses")) or DEFAULT_OPP_STATUSES
        page_size = self.PAGE_SIZE
        pause = config.get("rate_limit_seconds")

        # Una búsqueda por keyword; sin keywords, una sola con keyword="".
        keywords = config.get("keywords") or settings.keywords
        terminos = [k for k in (_txt(kw) for kw in keywords) if k] if keywords else []
        if not terminos:
            terminos = [""]

        # Dedupe global por id (una convocatoria puede matchear varias keywords).
        vistos: set[str] = set()
        resultados: list[RawConvocatoria] = []

        logger.info(
            "Grants.gov: fetch keywords=%s oppStatuses=%s max_paginas=%s page_size=%s",
            terminos,
            opp_statuses,
            max_paginas,
            page_size,
        )

        with get_http_client(pause_seconds=pause) as client:
            for termino in terminos:
                offset = 0
                for _pagina in range(max_paginas):
                    body = {
                        "rows": page_size,
                        "keyword": termino,
                        "oppStatuses": opp_statuses,
                        "startRecordNum": offset,
                    }
                    # Errores transitorios (429/5xx/red) los reintenta el
                    # HttpClient y, agotados, emergen como ConnectorError tipado.
                    response = client.post(SEARCH_URL, json=body)
                    try:
                        payload = response.json()
                    except ValueError as exc:
                        raise ParseError(
                            f"Grants.gov: respuesta no es JSON válido "
                            f"(keyword={termino!r}, offset={offset})"
                        ) from exc

                    hits = self._opp_hits(payload)
                    for hit in hits:
                        raw = self._map(hit)
                        if raw is None:
                            continue
                        if raw.id_externo in vistos:
                            continue
                        vistos.add(raw.id_externo)
                        resultados.append(raw)

                    # Última página: menos registros que el tamaño de página.
                    if len(hits) < page_size:
                        break
                    offset += page_size

        logger.info("Grants.gov: %s convocatorias mapeadas", len(resultados))
        return resultados
