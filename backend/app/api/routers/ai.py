"""Router de la capa de IA. Contrato nuevo en `docs/ai-contract.md`.

El router SOLO orquesta (request -> service -> response). Toda la lógica vive
en `app.api.services.ai`. Incluye un rate-limit básico en memoria por IP para
proteger las cuotas gratuitas de OpenRouter y no saturar Ollama.
"""

import threading
import time
from collections import defaultdict, deque

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.ai.schemas import (
    AIBusquedaRequest,
    AIBusquedaResponse,
    AIResumenResponse,
    AISoporteRequest,
    AISoporteResponse,
)
from app.api.deps import get_db
from app.api.services import ai as service

router = APIRouter(tags=["ia"])

# --- Rate limit en memoria (ventana deslizante por IP) --------------------
# Suficiente para un despliegue de un solo proceso uvicorn. No persiste entre
# reinicios (aceptable: es una salvaguarda anti-abuso, no un contador contable).
_RATE_MAX = 20          # peticiones...
_RATE_WINDOW = 60.0     # ...por esta ventana (segundos) y por IP.
_hits: dict[str, deque] = defaultdict(deque)
_lock = threading.Lock()


def _client_ip(request: Request) -> str:
    """IP del cliente. Respeta X-Forwarded-For (la app corre tras nginx)."""
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "desconocido"


def rate_limit(request: Request) -> None:
    """Dependencia: aplica el rate-limit por IP. Lanza 429 si se excede."""
    ahora = time.monotonic()
    ip = _client_ip(request)
    with _lock:
        cola = _hits[ip]
        while cola and (ahora - cola[0]) > _RATE_WINDOW:
            cola.popleft()
        if len(cola) >= _RATE_MAX:
            raise HTTPException(
                status_code=429,
                detail="Demasiadas peticiones a la IA. Espera un momento e intenta de nuevo.",
            )
        cola.append(ahora)


@router.post(
    "/buscar",
    response_model=AIBusquedaResponse,
    summary="Búsqueda en lenguaje natural (IA traduce a filtros reales)",
)
def buscar(
    body: AIBusquedaRequest,
    db: Session = Depends(get_db),
    _rl: None = Depends(rate_limit),
) -> AIBusquedaResponse:
    """La IA interpreta la pregunta y devuelve resultados REALES de la BD.

    Siempre 200. `ia_disponible=false` indica que se usó búsqueda por texto
    plano porque la IA no estaba disponible.
    """
    return service.buscar(db, body.pregunta)


@router.post(
    "/convocatorias/{convocatoria_id}/resumen",
    response_model=AIResumenResponse,
    summary="Resumen generado por IA de una convocatoria real",
)
def resumen(
    convocatoria_id: int,
    db: Session = Depends(get_db),
    _rl: None = Depends(rate_limit),
) -> AIResumenResponse:
    """Resume la descripción/requisitos reales. 404 si la convocatoria no existe."""
    resultado = service.resumir(db, convocatoria_id)
    if resultado is None:
        raise HTTPException(status_code=404, detail="Convocatoria no encontrada")
    return resultado


@router.post(
    "/soporte",
    response_model=AISoporteResponse,
    summary="Soporte técnico de uso (basado en el manual real)",
)
def soporte(
    body: AISoporteRequest,
    _rl: None = Depends(rate_limit),
) -> AISoporteResponse:
    """Responde dudas de uso con el manual como contexto. Degrada con gracia."""
    return service.soporte(body.pregunta)
