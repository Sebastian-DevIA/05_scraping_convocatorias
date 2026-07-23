"""Lógica de negocio de la capa de IA (asistente, resumen, soporte).

Regla dura: la IA NUNCA inventa datos. Aquí solo (a) traducimos lenguaje
natural a filtros y reutilizamos `listar_convocatorias` (resultados REALES de
Postgres); (b) resumimos texto que YA existe en la BD; (c) respondemos soporte
con el manual real. Ante cualquier fallo del proveedor, degradamos con gracia.
"""

import json
import logging
import re

from sqlalchemy.orm import Session

from app.ai import client, prompts
from app.ai.errors import AIError, AIUnavailableError
from app.ai.schemas import (
    AIBusquedaResponse,
    AIFiltrosExtraidos,
    AIResumenResponse,
    AISoporteResponse,
)
from app.api.deps import ConvocatoriaFiltros, PaginacionParams
from app.api.services import convocatorias as conv_service
from app.api.deps import ORDEN_DEFAULT

logger = logging.getLogger(__name__)

_MSG_NO_DISPONIBLE = (
    "El servicio de IA no está disponible ahora mismo. Intenta de nuevo más "
    "tarde; el resto de la aplicación sigue funcionando con normalidad."
)

# Campos de filtro que el modelo puede aportar (los demás se fijan a None).
_CAMPOS_FILTRO = (
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


def _filtros(**valores) -> ConvocatoriaFiltros:
    """Construye ConvocatoriaFiltros con TODOS los campos explícitos.

    Necesario porque los defaults del dataclass son objetos `Query` (para
    FastAPI); instanciarlo a mano exige fijar cada campo a un valor real.
    """
    base = {campo: valores.get(campo) for campo in _CAMPOS_FILTRO}
    base["orden"] = valores.get("orden", ORDEN_DEFAULT)
    return ConvocatoriaFiltros(**base)


def _extraer_json(texto: str) -> dict:
    """Extrae el primer objeto JSON del texto del modelo (tolera ``` y ruido)."""
    limpio = texto.strip()
    # Quita cercas de código markdown si las hubiera.
    limpio = re.sub(r"^```(?:json)?", "", limpio).strip()
    limpio = re.sub(r"```$", "", limpio).strip()
    try:
        return json.loads(limpio)
    except json.JSONDecodeError:
        pass
    # Fallback: primer bloque {...} balanceado por búsqueda simple.
    inicio = limpio.find("{")
    fin = limpio.rfind("}")
    if inicio != -1 and fin != -1 and fin > inicio:
        return json.loads(limpio[inicio : fin + 1])
    raise ValueError("no se encontró JSON en la respuesta del modelo")


def buscar(db: Session, pregunta: str) -> AIBusquedaResponse:
    """Traduce la pregunta a filtros con IA y devuelve resultados REALES.

    Siempre responde (200): si la IA no está disponible o su salida no valida,
    cae al fallback de búsqueda por texto plano `q=<pregunta>`.
    """
    pregunta = pregunta.strip()
    ia_disponible = False
    fallback = True
    filtros_dict: dict = {"q": pregunta}

    try:
        crudo = client.complete(prompts.SYSTEM_EXTRACCION_FILTROS, pregunta)
        ia_disponible = True
        datos = _extraer_json(crudo)
        extraidos = AIFiltrosExtraidos.model_validate(datos)
        filtros_dict = extraidos.model_dump(exclude_none=True, mode="json")
        # Si el modelo no aportó ningún filtro útil, usamos la pregunta como `q`.
        if not filtros_dict:
            filtros_dict = {"q": pregunta}
        else:
            fallback = False
    except AIUnavailableError:
        logger.info("IA no disponible; búsqueda cae a texto plano.")
    except (AIError, ValueError, TypeError) as exc:
        # Proveedor respondió pero con JSON inválido / no validable.
        logger.warning("Salida de IA inválida; fallback a texto plano: %s", exc)

    filtros = _filtros(
        q=filtros_dict.get("q"),
        fuente=filtros_dict.get("fuente"),
        estado=filtros_dict.get("estado"),
        tipo=filtros_dict.get("tipo"),
        departamento=filtros_dict.get("departamento"),
        apto_fundaciones_nuevas=filtros_dict.get("apto_fundaciones_nuevas"),
        fecha_publicacion_desde=filtros_dict.get("fecha_publicacion_desde"),
        fecha_publicacion_hasta=filtros_dict.get("fecha_publicacion_hasta"),
        fecha_cierre_desde=filtros_dict.get("fecha_cierre_desde"),
        fecha_cierre_hasta=filtros_dict.get("fecha_cierre_hasta"),
        monto_min=filtros_dict.get("monto_min"),
        monto_max=filtros_dict.get("monto_max"),
    )
    paginacion = PaginacionParams(page=1, page_size=20)
    resultado = conv_service.listar_convocatorias(db, filtros, paginacion)

    return AIBusquedaResponse(
        filtros_interpretados=filtros_dict,
        ia_disponible=ia_disponible,
        fallback=fallback,
        resultado=resultado,
    )


def resumir(db: Session, convocatoria_id: int) -> AIResumenResponse | None:
    """Resume la descripción/requisitos REALES de una convocatoria.

    Devuelve None si la convocatoria no existe (el router responde 404).
    """
    conv = conv_service.obtener_convocatoria(db, convocatoria_id, include_raw=False)
    if conv is None:
        return None

    partes = [f"Título: {conv.titulo}"]
    if conv.entidad:
        partes.append(f"Entidad: {conv.entidad}")
    if conv.descripcion:
        partes.append(f"Descripción: {conv.descripcion}")
    if conv.requisitos:
        partes.append(f"Requisitos: {conv.requisitos}")
    texto = "\n\n".join(partes)

    try:
        resumen = client.complete(prompts.SYSTEM_RESUMEN, texto)
    except AIUnavailableError:
        return AIResumenResponse(resumen=None, ia_disponible=False, mensaje=_MSG_NO_DISPONIBLE)
    except AIError as exc:
        logger.warning("Error resumiendo con IA: %s", exc)
        return AIResumenResponse(resumen=None, ia_disponible=False, mensaje=_MSG_NO_DISPONIBLE)

    return AIResumenResponse(resumen=resumen, ia_disponible=True)


def soporte(pregunta: str) -> AISoporteResponse:
    """Responde una duda de uso con el manual real como contexto."""
    try:
        respuesta = client.complete(prompts.system_soporte(), pregunta.strip())
    except AIUnavailableError:
        return AISoporteResponse(respuesta=_MSG_NO_DISPONIBLE, ia_disponible=False)
    except AIError as exc:
        logger.warning("Error en soporte con IA: %s", exc)
        return AISoporteResponse(respuesta=_MSG_NO_DISPONIBLE, ia_disponible=False)

    return AISoporteResponse(respuesta=respuesta, ia_disponible=True)
