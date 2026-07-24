"""Schemas Pydantic v2 del histórico propio de gestión.

A diferencia del resto de schemas (que exponen datos REALES de las fuentes),
estos representan datos NUESTROS: a qué convocatorias nos postulamos con este
software y cuáles descartamos. Contrato en `docs/api-contract.md`.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.constants import EstadoGestion
from app.schemas.convocatoria import ConvocatoriaResponse


class GestionRequest(BaseModel):
    """Cuerpo de `PUT /convocatorias/{id}/gestion` (upsert de la marca)."""

    estado_gestion: EstadoGestion = Field(
        description=(
            "'postulada' = ya nos postulamos con este software; 'descartada' = "
            "no nos interesa. Ambos sacan la convocatoria de la búsqueda."
        )
    )
    responsable: str | None = Field(
        default=None,
        max_length=120,
        description="Quién del equipo hizo la marca (texto libre, sin login).",
    )
    fecha_postulacion: datetime | None = Field(
        default=None,
        description=(
            "Cuándo nos postulamos. Solo aplica a 'postulada'; si se omite se "
            "usa el momento actual. En 'descartada' se ignora y queda null."
        ),
    )
    notas: str | None = Field(default=None, description="Notas libres del equipo.")


class GestionResponse(BaseModel):
    """Registro de gestión (sin la convocatoria embebida)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    convocatoria_id: int
    estado_gestion: EstadoGestion
    responsable: str | None = None
    fecha_postulacion: datetime | None = None
    notas: str | None = None
    creado_en: datetime
    actualizado_en: datetime


class GestionItemResponse(GestionResponse):
    """Entrada del histórico: la marca + la convocatoria a la que pertenece."""

    convocatoria: ConvocatoriaResponse


class GestionPageResponse(BaseModel):
    """Página del histórico: `{items, total, page, page_size}`."""

    items: list[GestionItemResponse]
    total: int = Field(description="Total de registros que cumplen el filtro.")
    page: int = Field(description="Página actual (base 1).")
    page_size: int = Field(description="Tamaño de página.")
