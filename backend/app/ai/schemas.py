"""Schemas Pydantic v2 de la capa de IA (contrato en docs/ai-contract.md).

Son schemas NUEVOS y aparte de los de convocatorias (que siguen congelados).
"""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.constants import EstadoConvocatoria, TipoConvocatoria
from app.schemas.convocatoria import ConvocatoriaPageResponse

# Límite de longitud de la pregunta del usuario (acota el prompt). Coincide con
# el default de Settings.ai_max_pregunta_len; se aplica aquí para dar 422 limpio.
MAX_PREGUNTA = 500


class AIFiltrosExtraidos(BaseModel):
    """Filtros que el modelo propone a partir de la pregunta en lenguaje natural.

    Subconjunto validado de ConvocatoriaFiltros. Claves desconocidas del modelo
    se ignoran; valores fuera de los enums canónicos hacen fallar la validación
    (y el servicio cae entonces al fallback de texto plano).
    """

    model_config = ConfigDict(extra="ignore")

    q: str | None = None
    fuente: str | None = None
    estado: EstadoConvocatoria | None = None
    tipo: TipoConvocatoria | None = None
    departamento: str | None = None
    fecha_publicacion_desde: date | None = None
    fecha_publicacion_hasta: date | None = None
    fecha_cierre_desde: date | None = None
    fecha_cierre_hasta: date | None = None
    monto_min: Decimal | None = None
    monto_max: Decimal | None = None


class AIBusquedaRequest(BaseModel):
    """Pregunta en lenguaje natural para el asistente de búsqueda."""

    pregunta: str = Field(min_length=1, max_length=MAX_PREGUNTA)


class AIBusquedaResponse(BaseModel):
    """Resultado del asistente: filtros interpretados + resultados REALES.

    - `ia_disponible=True`: los filtros los interpretó la IA.
    - `ia_disponible=False`: la IA no estaba disponible; se usó `q=<pregunta>`.
    """

    filtros_interpretados: dict
    ia_disponible: bool
    fallback: bool = Field(
        default=False,
        description="True si se usó búsqueda por texto plano (IA no disponible o JSON inválido).",
    )
    resultado: ConvocatoriaPageResponse


class AIResumenResponse(BaseModel):
    """Resumen generado por IA de una convocatoria real. `resumen=None` si no disponible."""

    resumen: str | None = None
    ia_disponible: bool
    mensaje: str | None = Field(
        default=None, description="Aviso legible cuando la IA no está disponible."
    )


class AISoporteRequest(BaseModel):
    """Pregunta de soporte técnico sobre el uso de la herramienta."""

    pregunta: str = Field(min_length=1, max_length=MAX_PREGUNTA)


class AISoporteResponse(BaseModel):
    """Respuesta de soporte. Si `ia_disponible=False`, `respuesta` trae el aviso."""

    respuesta: str
    ia_disponible: bool
