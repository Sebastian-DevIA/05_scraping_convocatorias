"""Schemas Pydantic v2 (entrada `*Request`, salida `*Response`)."""

from app.schemas.convocatoria import (
    ConvocatoriaDetailResponse,
    ConvocatoriaExportRequest,
    ConvocatoriaPageResponse,
    ConvocatoriaResponse,
)
from app.schemas.ejecucion import EjecucionListResponse, EjecucionResponse
from app.schemas.fuente import FuenteListResponse, FuenteResponse
from app.schemas.gestion import (
    GestionItemResponse,
    GestionPageResponse,
    GestionRequest,
    GestionResponse,
)
from app.schemas.raw import RawConvocatoria
from app.schemas.stats import Conteo, ConteoPorFuente, StatsResponse

__all__ = [
    "RawConvocatoria",
    "ConvocatoriaResponse",
    "ConvocatoriaDetailResponse",
    "ConvocatoriaPageResponse",
    "ConvocatoriaExportRequest",
    "GestionRequest",
    "GestionResponse",
    "GestionItemResponse",
    "GestionPageResponse",
    "EjecucionResponse",
    "EjecucionListResponse",
    "FuenteResponse",
    "FuenteListResponse",
    "StatsResponse",
    "Conteo",
    "ConteoPorFuente",
]
