"""Conector Banco Mundial — API JSON de Procurement Notices.

Fuente: portal de contrataciones del Banco Mundial (World Bank Procurement
Notices). Se consulta el endpoint JSON público de búsqueda del banco.

Estrategia (verificada en vivo el 2026-07-23 contra la API real):
  - Listado paginado por `os` (offset) y `rows` (tamaño de página), ordenado por
    fecha de aviso (`srt=noticedate`), que devuelve los avisos más recientes
    primero. Se recorre hasta ``config["max_paginas"]`` páginas.
  - NOTA (verificado en vivo): la combinación ``order=DESC`` documentada rompe el
    backend actual con un ``400 Syntax error`` (el nuevo índice Azure Search
    rechaza el literal `"noticedate DESC"`). Solo se envía ``srt=noticedate``,
    que responde 200 y ya entrega el orden descendente por fecha. No se inventa
    ningún parámetro: se usa exactamente lo que la fuente acepta.

La respuesta es un objeto JSON con la forma::

    {"rows": N, "os": offset, "page": P, "total": "NNN", "procnotices": [ {...} ]}

Mapeo a `RawConvocatoria` (campos crudos reales de cada `procnotice`):
  id_externo   <- id                     titulo      <- bid_description | project_name
  descripcion  <- notice_text (HTML aplanado a texto legible con html_to_text)
  entidad      <- project_name           tipo        <- notice_type / procurement_group
  estado_fuente<- notice_status          modalidad   <- procurement_method_name
  pais         <- project_ctry_name (fallback "Global")
  fecha_publicacion <- noticedate (%d-%b-%Y -> UTC)
  fecha_cierre <- submission_date (ISO, sufijo Z soportado -> UTC)
  url_original <- https://projects.worldbank.org/en/projects-operations/procurement-detail/{id}
  raw          = registro completo

El listado NO expone monto fiable ni requisitos ni fecha de apertura, por eso
``monto``, ``moneda``, ``departamento``, ``ciudad``, ``fecha_apertura`` y
``requisitos`` quedan en None (nunca se inventan). Un registro sin `id` no tiene
URL construible y se descarta.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.connectors.base import BaseConnector, ParseError
from app.connectors.http import get_http_client
from app.schemas.raw import RawConvocatoria
from app.utils.text import html_to_text

logger = logging.getLogger(__name__)

# --- Endpoint y campos reales de la API (verificados en vivo) ---------------
API_URL = "https://search.worldbank.org/api/v2/procnotices"

F_ID = "id"
F_NOTICE_TYPE = "notice_type"
F_NOTICE_DATE = "noticedate"
F_NOTICE_STATUS = "notice_status"
F_NOTICE_TEXT = "notice_text"
F_CTRY = "project_ctry_name"
F_PROJECT_NAME = "project_name"
F_BID_DESCRIPTION = "bid_description"
F_PROC_GROUP = "procurement_group"
F_PROC_METHOD = "procurement_method_name"
F_SUBMISSION_DATE = "submission_date"

# Clave del arreglo de avisos dentro del objeto de respuesta.
K_PROCNOTICES = "procnotices"

# Formato de `noticedate` en el listado (ej. "22-Jul-2026").
NOTICE_DATE_FMT = "%d-%b-%Y"

# --- Defaults (overridables por `config`) ----------------------------------
DEFAULT_MAX_PAGINAS = 5
# País por defecto cuando la fuente no lo reporta (la fuente es global).
PAIS_DEFAULT_WB = "Global"


def _txt(value: object) -> str | None:
    """Normaliza a str no vacío o None (dato ausente -> None)."""
    if value is None:
        return None
    s = str(value).strip()
    return s or None


def _parse_notice_date(value: object) -> datetime | None:
    """`noticedate` (`%d-%b-%Y`, sin tz) -> datetime UTC. Imparseable -> None.

    La fecha no lleva zona horaria; se asume/normaliza a UTC.
    """
    s = _txt(value)
    if s is None:
        return None
    try:
        dt = datetime.strptime(s, NOTICE_DATE_FMT)
    except ValueError:
        return None
    return dt.replace(tzinfo=timezone.utc)


def _parse_iso_utc(value: object) -> datetime | None:
    """ISO (ej. `2026-07-22T00:00:00Z`) -> datetime UTC. Imparseable -> None.

    Fechas sin offset se asumen UTC; fechas con offset se convierten a UTC.
    """
    if value is None or not isinstance(value, str):
        return None
    s = value.strip()
    if not s:
        return None
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _map_tipo(notice_type: object, procurement_group: object) -> str:
    """Mapea `notice_type`/`procurement_group` al tipo canónico.

    El orden de comprobación importa: 'expression of interest' antes que 'rfp'
    (un EOI de consultoría contiene ambos matices y debe quedar como 'eoi').
    """
    text = " ".join(
        p for p in (_txt(notice_type), _txt(procurement_group)) if p
    ).lower()
    if "expression of interest" in text:
        return "eoi"
    if "request for proposal" in text or "consultant" in text:
        return "rfp"
    if any(
        k in text
        for k in ("invitation for bids", "goods", "works", "procurement", "contract")
    ):
        return "licitacion"
    if "grant" in text:
        return "subvencion"
    return "otro"


class WorldBankConnector(BaseConnector):
    """Conector del Banco Mundial (API JSON de Procurement Notices)."""

    codigo = "worldbank"
    nombre = "Banco Mundial (World Bank)"

    # Tamaño de página. Constante de clase para poder ajustarla en tests de
    # paginación sin necesitar cientos de registros reales.
    PAGE_SIZE = 100

    # --- Mapeo registro -> RawConvocatoria ---------------------------------
    def _map(self, reg: dict) -> RawConvocatoria | None:
        """Mapea un aviso crudo. Devuelve None si debe descartarse."""
        if not isinstance(reg, dict):
            logger.warning("WorldBank: registro no es objeto JSON, descartado")
            return None

        id_externo = _txt(reg.get(F_ID))
        if not id_externo:
            # Sin `id` no hay URL original construible -> se descarta.
            logger.warning("WorldBank: registro sin id (sin url_original), descartado")
            return None

        titulo = _txt(reg.get(F_BID_DESCRIPTION)) or _txt(reg.get(F_PROJECT_NAME))
        if not titulo:
            logger.warning(
                "WorldBank: registro sin titulo (id=%s), descartado", id_externo
            )
            return None

        url = (
            "https://projects.worldbank.org/en/projects-operations/"
            f"procurement-detail/{id_externo}"
        )

        # estado_fuente es obligatorio (str); crudo tal como lo reporta la fuente.
        estado = _txt(reg.get(F_NOTICE_STATUS)) or ""

        return RawConvocatoria(
            id_externo=id_externo,
            titulo=titulo,
            # notice_text llega como fragmento HTML -> se aplana a texto legible.
            descripcion=html_to_text(reg.get(F_NOTICE_TEXT)),
            entidad=_txt(reg.get(F_PROJECT_NAME)),
            tipo=_map_tipo(reg.get(F_NOTICE_TYPE), reg.get(F_PROC_GROUP)),
            estado_fuente=estado,
            modalidad=_txt(reg.get(F_PROC_METHOD)),
            # El listado no expone monto/moneda fiables -> None.
            monto=None,
            moneda=None,
            departamento=None,
            ciudad=None,
            pais=_txt(reg.get(F_CTRY)) or PAIS_DEFAULT_WB,
            fecha_publicacion=_parse_notice_date(reg.get(F_NOTICE_DATE)),
            # La fuente no expone fecha de apertura ni requisitos -> None.
            fecha_apertura=None,
            fecha_cierre=_parse_iso_utc(reg.get(F_SUBMISSION_DATE)),
            requisitos=None,
            url_original=url,
            raw=reg,
        )

    # --- API del conector --------------------------------------------------
    def fetch(self, config: dict) -> list[RawConvocatoria]:
        config = config or {}
        try:
            max_paginas = int(config.get("max_paginas") or DEFAULT_MAX_PAGINAS)
        except (TypeError, ValueError):
            max_paginas = DEFAULT_MAX_PAGINAS
        page_size = self.PAGE_SIZE
        pause = config.get("rate_limit_seconds")

        resultados: list[RawConvocatoria] = []
        offset = 0

        logger.info(
            "WorldBank: fetch max_paginas=%s page_size=%s", max_paginas, page_size
        )

        with get_http_client(pause_seconds=pause) as client:
            for _pagina in range(max_paginas):
                params = {
                    "format": "json",
                    "rows": page_size,
                    "os": offset,
                    "srt": F_NOTICE_DATE,
                }
                # Errores transitorios (429/5xx/red) ya se reintentan en el
                # HttpClient y, agotados, emergen como ConnectorError tipado.
                response = client.get(API_URL, params=params)
                try:
                    payload = response.json()
                except ValueError as exc:
                    raise ParseError(
                        f"WorldBank: respuesta no es JSON válido en offset {offset}"
                    ) from exc
                if not isinstance(payload, dict):
                    raise ParseError(
                        f"WorldBank: se esperaba un objeto JSON, llegó {type(payload).__name__}"
                    )
                registros = payload.get(K_PROCNOTICES)
                if not isinstance(registros, list):
                    raise ParseError(
                        f"WorldBank: '{K_PROCNOTICES}' no es una lista en offset {offset}"
                    )

                for reg in registros:
                    raw = self._map(reg)
                    if raw is not None:
                        resultados.append(raw)

                # Última página: menos registros que el tamaño de página.
                if len(registros) < page_size:
                    break
                offset += page_size

        logger.info("WorldBank: %s convocatorias mapeadas", len(resultados))
        return resultados
