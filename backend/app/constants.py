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

# --- Aptitud para fundaciones nuevas / primerizas --------------------------
# Flag DERIVADO (heurístico, trazable) que marca convocatorias potencialmente
# accesibles para fundaciones/organizaciones recién creadas y sin trayectoria.
# NO es un dato de la fuente: el pipeline lo calcula desde el CONTENIDO REAL
# (título + descripción + requisitos + tipo), comparando (sin acentos, en
# minúsculas, vía `fold_text`) contra estas listas. Editables sin tocar lógica.
#
# Semántica honesta: True = se hallaron señales de apertura a nuevas
# organizaciones y NINGUNA señal descalificante. False = sin evidencia (NO es
# una afirmación de "no apto"). Puede tener falsos positivos/negativos: SIEMPRE
# verificar en la publicación oficial (coherente con el resto de la app).

# Señales POSITIVAS: sugieren apertura a organizaciones nuevas/primerizas.
SEÑALES_FUNDACIONES_NUEVAS: tuple[str, ...] = (
    "primera vez",
    "primeriza",
    "primerizas",
    "nueva organizacion",
    "nuevas organizaciones",
    "organizaciones nuevas",
    "recien creada",
    "recien creadas",
    "recien constituida",
    "recien constituidas",
    "organizaciones emergentes",
    "emergente",
    "capital semilla",
    "semilla",
    "emprendimiento",
    "emprendedor",
    "emprendedora",
    "startup",
    "fortalecimiento organizacional",
    "fortalecimiento institucional",
    "sin experiencia previa",
    "no se requiere experiencia",
    "no requiere experiencia",
    "sin trayectoria",
    "microsubvencion",
    "micro subvencion",
    "pequenas organizaciones",
    "small grant",
    "small grants",
    "seed grant",
    "seed funding",
    "first-time",
    "first time applicant",
    "new organization",
    "new organizations",
    "grassroots",
    "startup grant",
)

# Señales DESCALIFICANTES: exigen trayectoria/experiencia -> NO apto para nuevas.
SEÑALES_EXPERIENCIA_REQUERIDA: tuple[str, ...] = (
    "experiencia minima",
    "minimo de experiencia",
    "anos de experiencia",
    "años de experiencia",
    "experiencia de al menos",
    "experiencia acreditada",
    "experiencia comprobada",
    "experiencia demostrable",
    "trayectoria minima",
    "trayectoria de al menos",
    "years of experience",
    "minimum experience",
    "proven experience",
    "demonstrated experience",
    "capacidad financiera minima",
    "patrimonio minimo",
)

# --- Otros -----------------------------------------------------------------
PAIS_DEFAULT = "Colombia"
