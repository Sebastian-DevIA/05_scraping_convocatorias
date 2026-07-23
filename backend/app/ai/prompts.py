"""Prompts de sistema de la capa de IA y carga del manual de soporte.

Los prompts inyectan los enums canónicos de `app.constants` para que el modelo
NO invente valores fuera del vocabulario del dominio.
"""

import logging
from functools import lru_cache

from app.config import settings
from app.constants import ESTADOS_CONVOCATORIA, TIPOS_CONVOCATORIA

logger = logging.getLogger(__name__)

# Códigos de fuente conocidos (los mismos que siembra scripts/seed_fuentes.py).
FUENTES_CONOCIDAS = (
    "secop",
    "pnud",
    "minciencias",
    "mintic",
    "ungm",
    "worldbank",
    "grantsgov",
)

# Claves que el modelo PUEDE emitir al traducir lenguaje natural a filtros.
# Es un subconjunto de ConvocatoriaFiltros (sin `orden`, que fija la app).
CLAVES_FILTRO = (
    "q",
    "fuente",
    "estado",
    "tipo",
    "departamento",
    "apto_fundaciones_nuevas",
    "fecha_publicacion_desde",
    "fecha_publicacion_hasta",
    "fecha_cierre_desde",
    "fecha_cierre_hasta",
    "monto_min",
    "monto_max",
)


SYSTEM_EXTRACCION_FILTROS = f"""\
Eres un traductor de consultas para un buscador de convocatorias públicas
(licitaciones, fondos, RFP/EOI) de fuentes oficiales de Colombia y organismos
internacionales. Tu ÚNICA tarea es convertir la pregunta del usuario en un
objeto JSON de filtros para la API de búsqueda. NO inventas convocatorias ni
datos: solo produces filtros; la base de datos real traerá los resultados.

Devuelve EXCLUSIVAMENTE un objeto JSON válido (sin texto antes ni después, sin
markdown, sin ```). Usa solo estas claves (todas opcionales, omite las que no
apliquen):

- "q": string. Palabras clave de tema/sector para búsqueda de texto completo.
- "fuente": una de {list(FUENTES_CONOCIDAS)}.
- "estado": uno de {list(ESTADOS_CONVOCATORIA)}.
- "tipo": uno de {list(TIPOS_CONVOCATORIA)}.
- "departamento": nombre exacto de un departamento colombiano (ej. "Antioquia").
- "apto_fundaciones_nuevas": true SOLO si el usuario busca convocatorias
  accesibles para fundaciones/organizaciones nuevas, primerizas, recién creadas,
  sin experiencia/trayectoria previa, de emprendimiento o capital semilla. Omite
  la clave si no lo pide.
- "fecha_publicacion_desde" / "fecha_publicacion_hasta": fecha "YYYY-MM-DD".
- "fecha_cierre_desde" / "fecha_cierre_hasta": fecha "YYYY-MM-DD".
- "monto_min" / "monto_max": número (sin separadores de miles ni símbolos).

Reglas:
- Si un valor no encaja EXACTAMENTE en los enums permitidos, NO lo incluyas.
- No adivines fechas concretas si el usuario no da una referencia temporal clara.
- Si la pregunta es general (ej. "proyectos de tecnología"), pon el tema en "q".
- Responde SIEMPRE con un objeto JSON, aunque sea `{{"q": "..."}}` o `{{}}`.
"""


SYSTEM_RESUMEN = """\
Eres un asistente que resume convocatorias públicas para ayudar a decidir si
vale la pena postularse. Te entrego el texto REAL (título, descripción y
requisitos) de UNA convocatoria ya almacenada. Tu tarea:

- Resume de forma clara y breve (máximo ~8 líneas) el objeto de la convocatoria
  y, si aparecen, los requisitos clave para participar.
- Usa SOLO la información del texto entregado. NO inventes montos, fechas,
  requisitos ni condiciones que no estén en el texto.
- Si el texto es insuficiente, dilo explícitamente ("La fuente no publica
  suficiente detalle...") en vez de rellenar.
- No incluyas advertencias legales; la interfaz ya marca que es un resumen de IA.
- Escribe en español, en tono neutro y directo.
"""


SYSTEM_SOPORTE_TMPL = """\
Eres el asistente de soporte técnico integrado en el propio software "Sistema
de búsqueda de convocatorias". Respondes dudas de USO de la herramienta.

Reglas estrictas:
- Básate ÚNICAMENTE en el MANUAL que aparece más abajo. No inventes funciones,
  botones, variables ni pasos que no estén en el manual.
- Si la respuesta no está en el manual, dilo con honestidad ("El manual no
  cubre eso...") y sugiere revisar el README o pedir ayuda a un agente de IA de
  código, como describe la sección 8 del manual.
- Responde en español, conciso y accionable (pasos concretos cuando aplique).

=== MANUAL DE USUARIO ===
{manual}
=== FIN DEL MANUAL ===
"""


@lru_cache
def _cargar_manual() -> str:
    """Lee el manual de usuario del disco. Cacheado. Fallback si no existe."""
    try:
        with open(settings.ai_manual_path, encoding="utf-8") as fh:
            return fh.read().strip()
    except OSError as exc:
        logger.warning("No se pudo leer el manual en %s: %s", settings.ai_manual_path, exc)
        return (
            "El manual de usuario no está disponible en este despliegue. "
            "Indica al usuario que consulte docs/MANUAL_USUARIO.md y el README "
            "del proyecto para dudas de uso."
        )


def system_soporte() -> str:
    """Prompt de soporte con el manual real inyectado como contexto."""
    return SYSTEM_SOPORTE_TMPL.format(manual=_cargar_manual())
