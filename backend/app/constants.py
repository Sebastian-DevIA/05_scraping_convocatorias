"""Valores canónicos del dominio (contrato compartido entre capas).

Se centralizan aquí para que modelos, schemas, pipeline y conectores usen el
mismo vocabulario. NO modificar en Fase 1 sin coordinar (rompe el contrato).
"""

from typing import Literal

# --- Convocatoria: estado canónico ----------------------------------------
# El pipeline mapea el `estado_fuente` (texto libre de cada fuente) a uno de estos.
EstadoConvocatoria = Literal[
    "abierta",
    "cerrada",
    "adjudicada",
    "vencida",
    "desconocido",
]
ESTADOS_CONVOCATORIA: tuple[str, ...] = (
    "abierta",
    "cerrada",
    "adjudicada",
    "vencida",
    "desconocido",
)

# --- Convocatoria: tipo ----------------------------------------------------
TipoConvocatoria = Literal[
    "licitacion",
    "subvencion",
    "fondo",
    "rfp",
    "eoi",
    "otro",
]
TIPOS_CONVOCATORIA: tuple[str, ...] = (
    "licitacion",
    "subvencion",
    "fondo",
    "rfp",
    "eoi",
    "otro",
)

# --- Fuente: tipo de acceso ------------------------------------------------
TipoFuente = Literal["api", "html", "js"]
TIPOS_FUENTE: tuple[str, ...] = ("api", "html", "js")

# --- Ejecucion: trigger y estado ------------------------------------------
TriggerEjecucion = Literal["cron", "manual"]
TRIGGERS_EJECUCION: tuple[str, ...] = ("cron", "manual")

EstadoEjecucion = Literal["en_curso", "ok", "parcial", "error"]
ESTADOS_EJECUCION: tuple[str, ...] = ("en_curso", "ok", "parcial", "error")

# --- Otros -----------------------------------------------------------------
PAIS_DEFAULT = "Colombia"
