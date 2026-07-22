"""Schemas Pydantic v2 (entrada `*Request`, salida `*Response`)."""

from app.schemas.convocatoria import (
    ConvocatoriaDetailResponse,
    ConvocatoriaPageResponse,
    ConvocatoriaResponse,
)
from app.schemas.ejecucion import EjecucionListResponse, EjecucionResponse
from app.schemas.fuente import FuenteListResponse, FuenteResponse
from app.schemas.raw import RawConvocatoria
from app.schemas.stats import Conteo, ConteoPorFuente, StatsResponse

__all__ = [
    "RawConvocatoria",
    "ConvocatoriaResponse",
    "ConvocatoriaDetailResponse",
    "ConvocatoriaPageResponse",
    "EjecucionResponse",
    "EjecucionListResponse",
    "FuenteResponse",
    "FuenteListResponse",
    "StatsResponse",
    "Conteo",
    "ConteoPorFuente",
]
