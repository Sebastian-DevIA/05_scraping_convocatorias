"""Schemas Pydantic v2 de `ejecuciones` (salud de conectores)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.constants import EstadoEjecucion, TriggerEjecucion


class EjecucionResponse(BaseModel):
    """Una corrida de un conector."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    fuente_id: int
    trigger: TriggerEjecucion
    inicio: datetime
    fin: datetime | None = None
    estado: EstadoEjecucion

    items_obtenidos: int
    items_nuevos: int
    items_actualizados: int
    items_marcados_cerrados: int

    error_mensaje: str | None = None


class EjecucionListResponse(BaseModel):
    """Historial de ejecuciones de una fuente."""

    items: list[EjecucionResponse]
    total: int = Field(description="Total de ejecuciones registradas para la fuente.")
