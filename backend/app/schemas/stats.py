"""Schemas Pydantic v2 de `GET /stats` (métricas del dashboard)."""

from pydantic import BaseModel, Field


class Conteo(BaseModel):
    """Par clave/total genérico (para agrupaciones por estado, departamento...)."""

    clave: str = Field(description="Valor agrupado (estado, departamento, etc.).")
    total: int


class ConteoPorFuente(BaseModel):
    """Conteo agrupado por fuente."""

    codigo: str
    nombre: str
    total: int


class StatsResponse(BaseModel):
    """Métricas agregadas para el dashboard."""

    total: int = Field(description="Total de convocatorias almacenadas.")
    abiertas: int = Field(description="Convocatorias en estado 'abierta'.")
    nuevas_7d: int = Field(description="Nuevas en los últimos 7 días (primera_vez_visto).")
    cierran_7d: int = Field(description="Abiertas cuyo cierre ocurre en los próximos 7 días.")

    por_fuente: list[ConteoPorFuente] = Field(default_factory=list)
    por_estado: list[Conteo] = Field(default_factory=list)
    por_departamento: list[Conteo] = Field(default_factory=list)
