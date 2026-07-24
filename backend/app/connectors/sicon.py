"""Conector SICON — convocatorias distritales de cultura de Bogotá (API JSON).

Fuente: SICON, el sistema de convocatorias de la Secretaría de Cultura,
Recreación y Deporte de Bogotá. Es la plataforma ÚNICA del Distrito Capital
para convocatorias de fomento: agrega en un solo listado las convocatorias de
SCRD, IDARTES, FUGA, IDPC, OFB y demás entidades del sector cultura de Bogotá.
Es la fuente que enlazan los portales de esas entidades (idartes.gov.co e
idpc.gov.co publican tablas cuyos enlaces apuntan a `cultured.gov.co`, el
frontend público de SICON).

Convocatorias territoriales por definición (entidades del orden distrital), por
eso todos los registros salen con ``ambito_fuente="Territorial"``.

Estrategia (verificada en vivo el 2026-07-23 contra la API real):
  - El backend exige un TOKEN público que el propio frontend descarga en claro
    desde ``https://cultured.gov.co/config/config.txt``. El archivo tiene la
    forma ``<token>{{<timestamp de emisión>}}``; se toma lo anterior a ``{{``.
    NO es un secreto nuestro: se sirve sin autenticación a cualquier visitante y
    rota solo. Por eso no vive en `.env` ni en el repo, se pide en cada corrida.
  - El listado es ``POST .../DrupalWS/convocatorias_publicadas`` con el cuerpo
    como **formulario** (``application/x-www-form-urlencoded``). Verificado en
    vivo: con cuerpo JSON, con los parámetros en la query o por GET la API
    responde ``{"error":2,"respuesta":"El token no es correcto"}``; solo el
    cuerpo de formulario funciona. De ahí el uso de ``client.post(..., data=)``.
  - Paginación por ``offset`` + ``limit``. La respuesta trae
    ``total_registros_sin_filtro`` con el total real del catálogo.

La respuesta es un objeto JSON con la forma::

    {"error": 0, "total_registros": N, "total_registros_sin_filtro": M,
     "respuesta": [ {...} ]}

``error`` distinto de 0 es un error de negocio de la fuente (ej. token vencido)
y se traduce a `ParseError` en vez de devolver una lista vacía silenciosa.

Mapeo a `RawConvocatoria` (campos crudos reales de cada registro):
  id_externo   <- id                      titulo      <- nombre
  descripcion  <- justificacion (HTML aplanado con html_to_text)
  entidad      <- entidad (sigla cruda: 'SCRD' | 'IDARTES' | 'FUGA' | ...)
  tipo         <- derivado de tipo_programa + nombre (ver `_map_tipo`)
  estado_fuente<- estado (CRUDO: 'Publicada' | 'Publicada Cerrada'); el pipeline
                  lo mapea al estado canónico, el conector NO
  modalidad    <- tipo_programa           ambito_fuente = "Territorial"
  monto        <- distribucion_estimulos.valor_total_estimulos  (moneda COP)
  fecha_publicacion / fecha_apertura / fecha_cierre <- cronograma[], por el
                  `tipo_evento` exacto correspondiente (hora legal de Bogotá,
                  UTC-05:00 fijo, convertida a UTC)
  requisitos   <- tipo_de_participante[] (quién puede postularse y con qué
                  condiciones; es literalmente el apartado de requisitos)
  url_original <- https://cultured.gov.co/detalle/convocatorias/{id}
  raw          = registro completo

El listado no expone fecha de apertura de sobres, ciudad fina ni otros campos:
lo ausente queda en None (nunca se inventa). Un registro sin `id` no tiene URL
construible y se descarta.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation

from app.connectors.base import BaseConnector, ParseError
from app.connectors.http import get_http_client
from app.schemas.raw import RawConvocatoria
from app.utils.text import fold_text, html_to_text

logger = logging.getLogger(__name__)

# --- Endpoints reales (verificados en vivo) --------------------------------
TOKEN_URL = "https://cultured.gov.co/config/config.txt"
API_URL = "https://sicon.scrd.gov.co/crud_SCRD_pv/api/DrupalWS/convocatorias_publicadas"
DETALLE_URL = "https://cultured.gov.co/detalle/convocatorias/{id}"

# Separador del timestamp dentro de config.txt: "<token>{{<fecha de emisión>}}".
TOKEN_SEP = "{{"

# --- Campos reales del registro --------------------------------------------
F_ID = "id"
F_NOMBRE = "nombre"
F_ESTADO = "estado"
F_ENTIDAD = "entidad"
F_JUSTIFICACION = "justificacion"
F_TIPO_PROGRAMA = "tipo_programa"
F_CRONOGRAMA = "cronograma"
F_DISTRIBUCION = "distribucion_estimulos"
F_PARTICIPANTES = "tipo_de_participante"

# Claves de la respuesta.
K_ERROR = "error"
K_RESPUESTA = "respuesta"

# Eventos del cronograma que aportan fechas. Se comparan por igualdad EXACTA
# (tras `fold_text`) y no por subcadena: el cronograma real trae eventos como
# "Fecha máxima para postularse como jurado..." o "Fecha máxima de publicación
# de resolución de ganadores" que NO son la publicación/apertura/cierre de la
# convocatoria. Si la fuente renombra un evento preferimos None + warning antes
# que colgar una fecha equivocada.
EV_PUBLICACION = "fecha de publicacion"
EV_APERTURA = "fecha de apertura"
EV_CIERRE = "fecha de cierre"

# Formatos reales de `cronograma[].fecha_inicio` (conviven ambos en la fuente).
FECHA_FMTS = ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S")

# Las fechas se publican en hora legal colombiana ("5:00 pm hora legal
# colombiana" según el propio cronograma). Colombia es UTC-05:00 fijo (no aplica
# horario de verano), así que basta un offset constante para normalizar a UTC.
TZ_BOGOTA = timezone(timedelta(hours=-5))

# `ambito_fuente` CRUDO: SICON solo publica convocatorias de entidades del
# Distrito Capital. El pipeline lo mapea al ámbito canónico.
AMBITO_SICON = "Territorial"

# Ubicación fija de la fuente: SICON es la plataforma ÚNICA del Distrito Capital
# (SCRD, IDARTES, FUGA, IDPC, OFB...). No es un dato inventado —es el hecho que
# también justifica AMBITO_SICON="Territorial"—: todas sus convocatorias son de
# Bogotá. Se usa la MISMA nomenclatura que SECOP (verificada en su dataset) para
# que los filtros por departamento/ciudad crucen ambas fuentes.
DEPARTAMENTO_SICON = "Distrito Capital de Bogotá"
CIUDAD_SICON = "Bogotá"

# Moneda de los estímulos (la fuente los expresa siempre en pesos: "$ 350.000.000").
MONEDA_SICON = "COP"

# Señales de `tipo_programa` + `nombre` que identifican un estímulo/subvención.
SEÑALES_SUBVENCION = (
    "estimulo",
    "beca",
    "premio",
    "residencia",
    "apoyo",
    "concertado",
    "espectaculos publicos",
    "fomento",
)

# --- Defaults (overridables por `config`) ----------------------------------
DEFAULT_MAX_PAGINAS = 5


def _txt(value: object) -> str | None:
    """Normaliza a str no vacío o None (dato ausente -> None)."""
    if value is None:
        return None
    s = str(value).strip()
    return s or None


def _parse_fecha(value: object) -> datetime | None:
    """`cronograma[].fecha_inicio` -> datetime UTC. Imparseable/ausente -> None.

    Acepta los dos formatos que conviven en la fuente (`%Y-%m-%d %H:%M:%S` y
    `%Y/%m/%d %H:%M:%S`). El valor está en hora legal de Bogotá y se convierte
    a UTC. Nunca se inventa una fecha: si no parsea, None.
    """
    s = _txt(value)
    if s is None:
        return None
    for fmt in FECHA_FMTS:
        try:
            dt = datetime.strptime(s, fmt)
        except ValueError:
            continue
        return dt.replace(tzinfo=TZ_BOGOTA).astimezone(timezone.utc)
    return None


def _fecha_de_evento(cronograma: object, evento: str) -> datetime | None:
    """Busca en el cronograma el `tipo_evento` pedido y devuelve su fecha UTC."""
    if not isinstance(cronograma, list):
        return None
    for item in cronograma:
        if not isinstance(item, dict):
            continue
        if fold_text(item.get("tipo_evento")) == evento:
            return _parse_fecha(item.get("fecha_inicio"))
    return None


def _monto(value: object) -> Decimal | None:
    """`"$ 350.000.000"` -> Decimal. Ausente/imparseable -> None.

    Formato colombiano: `.` separa miles y `,` decimales. La fuente usa el
    literal `"$ 0"` como marcador de "sin monto informado" (no existe una
    convocatoria de estímulos por cero pesos), así que se devuelve None en vez
    de persistir un importe falso.
    """
    s = _txt(value)
    if s is None:
        return None
    limpio = s.replace("$", "").replace("\xa0", "").replace(" ", "")
    limpio = limpio.replace(".", "").replace(",", ".")
    try:
        monto = Decimal(limpio)
    except (InvalidOperation, ValueError):
        return None
    return monto or None


def _map_tipo(tipo_programa: object, nombre: object) -> str:
    """Mapea `tipo_programa`/`nombre` al tipo canónico.

    SICON publica programas de fomento cultural (Programa Distrital de
    Estímulos, Ley de espectáculos públicos, apoyos concertados): becas, premios
    y residencias que son subvenciones. Sin señal reconocible -> 'otro'.
    """
    texto = f"{fold_text(tipo_programa)} {fold_text(nombre)}"
    if any(s in texto for s in SEÑALES_SUBVENCION):
        return "subvencion"
    return "otro"


def _requisitos(participantes: object) -> str | None:
    """`tipo_de_participante[]` -> texto de requisitos. Sin datos -> None.

    Cada entrada trae `participante` ('Persona Natural', 'Persona Jurídica',
    'Agrupación'...) y una `descripcion` en HTML con las condiciones exigidas.
    Se aplana a texto legible conservando a quién aplica cada bloque.
    """
    if not isinstance(participantes, list):
        return None
    bloques: list[str] = []
    for item in participantes:
        if not isinstance(item, dict):
            continue
        quien = _txt(item.get("participante"))
        detalle = html_to_text(item.get("descripcion"))
        if quien and detalle:
            bloques.append(f"{quien}:\n{detalle}")
        elif quien:
            bloques.append(quien)
        elif detalle:
            bloques.append(detalle)
    return "\n\n".join(bloques) or None


class SiconConnector(BaseConnector):
    """Conector SICON (convocatorias distritales de cultura de Bogotá)."""

    codigo = "sicon"
    nombre = "SICON — Convocatorias de Cultura de Bogotá (SCRD, IDARTES, FUGA, IDPC)"

    # Tamaño de página. Constante de clase para poder ajustarla en tests de
    # paginación sin necesitar cientos de registros reales.
    PAGE_SIZE = 50

    # --- Token público -----------------------------------------------------
    def _obtener_token(self, client) -> str:
        """Descarga el token público que exige la API (mismo GET que el navegador)."""
        response = client.get(TOKEN_URL)
        token = response.text.split(TOKEN_SEP)[0].strip()
        if not token:
            raise ParseError(f"SICON: {TOKEN_URL} no devolvió token")
        return token

    # --- Mapeo registro -> RawConvocatoria ---------------------------------
    def _map(self, reg: dict) -> RawConvocatoria | None:
        """Mapea un registro crudo. Devuelve None si debe descartarse."""
        if not isinstance(reg, dict):
            logger.warning("SICON: registro no es objeto JSON, descartado")
            return None

        id_externo = _txt(reg.get(F_ID))
        if not id_externo:
            # Sin `id` no hay url_original construible -> se descarta.
            logger.warning("SICON: registro sin id (sin url_original), descartado")
            return None

        titulo = _txt(reg.get(F_NOMBRE))
        if not titulo:
            logger.warning("SICON: registro sin nombre (id=%s), descartado", id_externo)
            return None

        cronograma = reg.get(F_CRONOGRAMA)
        fecha_cierre = _fecha_de_evento(cronograma, EV_CIERRE)
        if fecha_cierre is None:
            logger.warning(
                "SICON: sin '%s' parseable (id=%s) -> fecha_cierre=None",
                EV_CIERRE,
                id_externo,
            )

        distribucion = reg.get(F_DISTRIBUCION)
        valor = (
            distribucion.get("valor_total_estimulos")
            if isinstance(distribucion, dict)
            else None
        )
        monto = _monto(valor)

        # estado_fuente es obligatorio (str); crudo tal como lo reporta la fuente.
        estado = _txt(reg.get(F_ESTADO)) or ""

        return RawConvocatoria(
            id_externo=id_externo,
            titulo=titulo,
            # `justificacion` llega como HTML -> se aplana a texto legible.
            descripcion=html_to_text(reg.get(F_JUSTIFICACION)),
            entidad=_txt(reg.get(F_ENTIDAD)),
            tipo=_map_tipo(reg.get(F_TIPO_PROGRAMA), titulo),
            estado_fuente=estado,
            modalidad=_txt(reg.get(F_TIPO_PROGRAMA)),
            monto=monto,
            moneda=MONEDA_SICON if monto is not None else None,
            # SICON es la plataforma del Distrito Capital: ubicación fija Bogotá
            # (misma nomenclatura que SECOP para que los filtros crucen).
            departamento=DEPARTAMENTO_SICON,
            ciudad=CIUDAD_SICON,
            pais="Colombia",
            fecha_publicacion=_fecha_de_evento(cronograma, EV_PUBLICACION),
            fecha_apertura=_fecha_de_evento(cronograma, EV_APERTURA),
            fecha_cierre=fecha_cierre,
            requisitos=_requisitos(reg.get(F_PARTICIPANTES)),
            ambito_fuente=AMBITO_SICON,
            url_original=DETALLE_URL.format(id=id_externo),
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

        logger.info("SICON: fetch max_paginas=%s page_size=%s", max_paginas, page_size)

        with get_http_client(pause_seconds=pause) as client:
            token = self._obtener_token(client)

            for _pagina in range(max_paginas):
                # La API solo acepta el cuerpo como formulario (verificado en
                # vivo); con JSON o query params responde "El token no es correcto".
                body = {"token": token, "offset": offset, "limit": page_size}
                # Errores transitorios (429/5xx/red) ya se reintentan en el
                # HttpClient y, agotados, emergen como ConnectorError tipado.
                response = client.post(API_URL, data=body)
                try:
                    payload = response.json()
                except ValueError as exc:
                    raise ParseError(
                        f"SICON: respuesta no es JSON válido en offset {offset}"
                    ) from exc
                if not isinstance(payload, dict):
                    raise ParseError(
                        f"SICON: se esperaba un objeto JSON, llegó {type(payload).__name__}"
                    )
                # `error != 0` es un error de negocio de la fuente (ej. token
                # vencido): se propaga en vez de devolver una lista vacía.
                if payload.get(K_ERROR) != 0:
                    raise ParseError(
                        f"SICON: la fuente respondió error={payload.get(K_ERROR)!r} "
                        f"({payload.get(K_RESPUESTA)!r}) en offset {offset}"
                    )
                registros = payload.get(K_RESPUESTA)
                if not isinstance(registros, list):
                    raise ParseError(
                        f"SICON: '{K_RESPUESTA}' no es una lista en offset {offset}"
                    )

                for reg in registros:
                    raw = self._map(reg)
                    if raw is not None:
                        resultados.append(raw)

                # Última página: menos registros que el tamaño de página.
                if len(registros) < page_size:
                    break
                offset += page_size

        logger.info("SICON: %s convocatorias mapeadas", len(resultados))
        return resultados
