"""Conector SECOP II — API Socrata de datos.gov.co (dataset `p6dx-8zbt`).

Fuente: portal de datos abiertos de Colombia, dataset "SECOP II - Procesos de
Contratación". Se consulta vía SoQL sobre el endpoint JSON de Socrata.

Estrategia (verificada en vivo el 2026-07-21 contra la API real):
  - Filtro server-side incremental por `fecha_de_publicacion_del > fecha_desde`
    (la `fecha_desde` la inyecta el runner desde la última ejecución OK; si no hay,
    se usa un default de los últimos ``DEFAULT_LOOKBACK_DAYS`` días).
  - `adjudicado = 'No'` (campo real confirmado) para quedarnos con procesos aún
    no adjudicados.
  - Filtro por palabras clave (``config["keywords"]``) mediante un OR de
    ``lower(campo) like '%keyword%'`` sobre el nombre Y la descripción del
    procedimiento. Se eligió `like` sobre `$q` (full-text) porque:
      * `$q` es difuso (relevancia/stemming) y produce falsos positivos que no
        contienen literalmente la palabra clave;
      * `like` es determinista, transparente y por-campo, lo que facilita la
        trazabilidad exigida (regla dura: cero datos inventados) y los tests.
    Limitaciones documentadas del `like`: es sensible a acentos (la keyword se
    busca tal cual, en minúsculas) y hace match por subcadena (una keyword muy
    corta puede generar coincidencias parciales). La calidad del filtro depende
    de cómo estén escritas las keywords en la config.
  - Paginación con `$limit`/`$offset` y `$order` estable (fecha + id) hasta
    ``config["max_paginas"]`` páginas.

Mapeo a `RawConvocatoria` (campos crudos reales del dataset):
  id_externo <- id_del_proceso            titulo      <- nombre_del_procedimiento
  descripcion<- descripci_n_del_procedimiento          entidad     <- entidad
  departamento<- departamento_entidad     ciudad      <- ciudad_entidad
  monto      <- precio_base (Decimal)      moneda      = "COP"
  modalidad  <- modalidad_de_contratacion  estado_fuente<- estado_del_procedimiento
  fecha_publicacion <- fecha_de_publicacion_del (ISO floating -> UTC)
  url_original <- urlproceso.url (OBLIGATORIA: sin ella el registro se descarta)
  raw        = registro completo

El dataset NO expone deadline de recepción de ofertas ni requisitos de
participación (viven en documentos adjuntos), por eso ``fecha_apertura``,
``fecha_cierre`` y ``requisitos`` quedan en None (nunca se inventan).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation

from app.config import settings
from app.connectors.base import BaseConnector, ParseError
from app.connectors.http import get_http_client
from app.schemas.raw import RawConvocatoria

logger = logging.getLogger(__name__)

# --- Endpoint y campos reales del dataset (verificados en vivo) -------------
DATASET_URL = "https://www.datos.gov.co/resource/p6dx-8zbt.json"

F_ID = "id_del_proceso"
F_NOMBRE = "nombre_del_procedimiento"
F_DESCRIPCION = "descripci_n_del_procedimiento"
F_ENTIDAD = "entidad"
F_DEPARTAMENTO = "departamento_entidad"
F_CIUDAD = "ciudad_entidad"
F_PRECIO = "precio_base"
F_MODALIDAD = "modalidad_de_contratacion"
F_ESTADO = "estado_del_procedimiento"
F_ESTADO_APERTURA = "estado_de_apertura_del_proceso"
F_ESTADO_RESUMEN = "estado_resumen"
F_FECHA_PUB = "fecha_de_publicacion_del"
F_ADJUDICADO = "adjudicado"
F_URL = "urlproceso"

# Orden estable para paginar por offset sin saltos/duplicados (fecha + id).
ORDER = f"{F_FECHA_PUB} ASC, {F_ID} ASC"

# --- Defaults (overridables por `config`) ----------------------------------
DEFAULT_MAX_PAGINAS = 5
DEFAULT_LOOKBACK_DAYS = 60
MONEDA = "COP"


def _txt(value: object) -> str | None:
    """Normaliza a str no vacío o None (dato ausente -> None)."""
    if value is None:
        return None
    s = str(value).strip()
    return s or None


def _parse_decimal(value: object) -> Decimal | None:
    """precio_base -> Decimal. Imparseable/ausente -> None (nunca inventa)."""
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    try:
        return Decimal(s)
    except (InvalidOperation, ValueError):
        return None


def _parse_dt_utc(value: object) -> datetime | None:
    """ISO de Socrata (floating, sin tz) -> datetime UTC. Imparseable -> None.

    Los timestamps de Socrata (`2026-01-02T00:00:00.000`) no llevan zona horaria;
    se asumen/convierten a UTC. Fechas ya con offset se convierten a UTC.
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


def _extract_url(urlproceso: object) -> str | None:
    """`urlproceso` es un tipo URL de Socrata: dict {"url": ...}. Extrae la URL."""
    if isinstance(urlproceso, dict):
        url = urlproceso.get("url")
        return url.strip() if isinstance(url, str) and url.strip() else None
    if isinstance(urlproceso, str):
        return urlproceso.strip() or None
    return None


class SecopConnector(BaseConnector):
    """Conector de SECOP II (API Socrata)."""

    codigo = "secop"
    nombre = "SECOP II"

    # Tamaño de página SoQL. Constante de clase para poder ajustarla en tests
    # de paginación sin necesitar 1000 registros reales.
    PAGE_SIZE = 1000

    # --- Construcción del filtro SoQL --------------------------------------
    def _fecha_desde_soql(self, config: dict) -> str:
        """Devuelve la `fecha_desde` como timestamp floating de Socrata.

        Prioriza ``config["fecha_desde"]`` (ISO, inyectada por el runner desde la
        última ejecución OK). Si falta o es imparseable, usa los últimos
        ``DEFAULT_LOOKBACK_DAYS`` días.
        """
        raw = config.get("fecha_desde")
        dt: datetime | None = None
        if isinstance(raw, datetime):
            dt = raw if raw.tzinfo else raw.replace(tzinfo=timezone.utc)
            dt = dt.astimezone(timezone.utc)
        elif raw is not None:
            dt = _parse_dt_utc(raw)
            if dt is None:
                logger.warning(
                    "SECOP: fecha_desde imparseable %r; usando últimos %s días",
                    raw,
                    DEFAULT_LOOKBACK_DAYS,
                )
        if dt is None:
            dt = datetime.now(timezone.utc) - timedelta(days=DEFAULT_LOOKBACK_DAYS)
        # Socrata espera un floating timestamp (sin tz) en el literal SoQL.
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

    def _keyword_clause(self, keywords: list[str]) -> str | None:
        """OR de `lower(nombre|descripcion) like '%kw%'` para cada keyword.

        Devuelve None si no hay keywords válidas (sin filtro por keyword).
        """
        partes: list[str] = []
        for kw in keywords:
            k = _txt(kw)
            if not k:
                continue
            # SoQL: literales entre comillas simples; se escapan doblándolas.
            esc = k.lower().replace("'", "''")
            partes.append(
                f"(lower({F_NOMBRE}) like '%{esc}%' "
                f"OR lower({F_DESCRIPCION}) like '%{esc}%')"
            )
        if not partes:
            return None
        return "(" + " OR ".join(partes) + ")"

    def _build_where(self, config: dict) -> str:
        """Construye la cláusula `$where` completa (incremental + estado + keywords)."""
        clausulas = [
            f"{F_FECHA_PUB} > '{self._fecha_desde_soql(config)}'",
            f"{F_ADJUDICADO}='No'",
        ]
        keywords = config.get("keywords") or settings.keywords
        kw_clause = self._keyword_clause(keywords)
        if kw_clause:
            clausulas.append(kw_clause)
        return " AND ".join(clausulas)

    # --- Mapeo registro -> RawConvocatoria ---------------------------------
    def _map(self, reg: dict) -> RawConvocatoria | None:
        """Mapea un registro crudo. Devuelve None si debe descartarse."""
        if not isinstance(reg, dict):
            logger.warning("SECOP: registro no es objeto JSON, descartado")
            return None

        id_externo = _txt(reg.get(F_ID))
        url = _extract_url(reg.get(F_URL))
        if not url:
            logger.warning(
                "SECOP: registro sin url_original (id=%s), descartado", id_externo
            )
            return None

        titulo = _txt(reg.get(F_NOMBRE)) or _txt(reg.get(F_DESCRIPCION))
        if not id_externo or not titulo:
            logger.warning(
                "SECOP: registro sin id/titulo (id=%s), descartado", id_externo
            )
            return None

        # estado_fuente es obligatorio (str); cadena de fallbacks sobre campos reales.
        estado = (
            _txt(reg.get(F_ESTADO))
            or _txt(reg.get(F_ESTADO_APERTURA))
            or _txt(reg.get(F_ESTADO_RESUMEN))
            or ""
        )

        return RawConvocatoria(
            id_externo=id_externo,
            titulo=titulo,
            descripcion=_txt(reg.get(F_DESCRIPCION)),
            entidad=_txt(reg.get(F_ENTIDAD)),
            tipo="licitacion",
            estado_fuente=estado,
            modalidad=_txt(reg.get(F_MODALIDAD)),
            monto=_parse_decimal(reg.get(F_PRECIO)),
            moneda=MONEDA,
            departamento=_txt(reg.get(F_DEPARTAMENTO)),
            ciudad=_txt(reg.get(F_CIUDAD)),
            # pais: default "Colombia" (SECOP es fuente nacional).
            fecha_publicacion=_parse_dt_utc(reg.get(F_FECHA_PUB)),
            # El dataset no expone deadline de ofertas ni requisitos -> None.
            fecha_apertura=None,
            fecha_cierre=None,
            requisitos=None,
            url_original=url,
            raw=reg,
        )

    # --- API del conector --------------------------------------------------
    def fetch(self, config: dict) -> list[RawConvocatoria]:
        config = config or {}
        where = self._build_where(config)
        try:
            max_paginas = int(config.get("max_paginas") or DEFAULT_MAX_PAGINAS)
        except (TypeError, ValueError):
            max_paginas = DEFAULT_MAX_PAGINAS
        page_size = self.PAGE_SIZE
        pause = config.get("rate_limit_seconds")

        resultados: list[RawConvocatoria] = []
        offset = 0

        logger.info(
            "SECOP: fetch where=%s max_paginas=%s page_size=%s",
            where,
            max_paginas,
            page_size,
        )

        with get_http_client(pause_seconds=pause) as client:
            for _pagina in range(max_paginas):
                params = {
                    "$where": where,
                    "$order": ORDER,
                    "$limit": page_size,
                    "$offset": offset,
                }
                # Errores transitorios (429/5xx/red) ya se reintentan en el
                # HttpClient y, agotados, emergen como ConnectorError tipado.
                response = client.get(DATASET_URL, params=params)
                try:
                    registros = response.json()
                except ValueError as exc:
                    raise ParseError(
                        f"SECOP: respuesta no es JSON válido en offset {offset}"
                    ) from exc
                if not isinstance(registros, list):
                    raise ParseError(
                        f"SECOP: se esperaba una lista JSON, llegó {type(registros).__name__}"
                    )

                for reg in registros:
                    raw = self._map(reg)
                    if raw is not None:
                        resultados.append(raw)

                # Última página: menos registros que el tamaño de página.
                if len(registros) < page_size:
                    break
                offset += page_size

        logger.info("SECOP: %s convocatorias mapeadas", len(resultados))
        return resultados
