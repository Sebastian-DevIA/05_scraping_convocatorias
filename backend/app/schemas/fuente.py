"""Schemas Pydantic v2 de `fuentes` (con última ejecución embebida = salud)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.constants import TipoFuente
from app.schemas.ejecucion import EjecucionResponse


class FuenteResponse(BaseModel):
    """Fuente con su última ejecución embebida (para el panel de salud)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    codigo: str
    nombre: str
    url_base: str
    tipo: TipoFuente
    activa: bool
    config: dict

    creado_en: datetime
    actualizado_en: datetime

    # Última corrida (None si nunca se ha ejecutado). Refleja la salud del conector.
    ultima_ejecucion: EjecucionResponse | None = Field(
        default=None,
        description="Última ejecución registrada de la fuente (salud del conector).",
    )


class FuenteListResponse(BaseModel):
    """Listado de fuentes."""

    items: list[FuenteResponse]
    total: int
