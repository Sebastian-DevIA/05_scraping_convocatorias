"""Punto de entrada de la API FastAPI.

Fase 0: solo el router health bajo /api/v1. Fase 1 (agente E) incluirá aquí los
routers de convocatorias, fuentes, stats y scraping (mismo prefijo /api/v1).
"""

from fastapi import APIRouter, FastAPI

from app import __version__
from app.api.routers import ai, convocatorias, fuentes, health, scraping, stats

app = FastAPI(
    title="Convocatorias API",
    version=__version__,
    description="API del Sistema automatizado de búsqueda de convocatorias.",
)

# Router raíz con el prefijo congelado del contrato REST.
api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(convocatorias.router, prefix="/convocatorias")
api_router.include_router(fuentes.router, prefix="/fuentes")
api_router.include_router(stats.router, prefix="/stats")
api_router.include_router(scraping.router, prefix="/scraping")
api_router.include_router(ai.router, prefix="/ai")

app.include_router(api_router)
