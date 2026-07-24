"""Routers del histórico propio de gestión.

Son dos routers porque cuelgan de prefijos distintos (ver `app.api.main`):
`router_convocatorias` -> /convocatorias/{id}/gestion (marcar/desmarcar) y
`router` -> /gestion (listado del histórico).
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.api.deps import PaginacionParams, get_db
from app.api.services import gestion as service
from app.constants import EstadoGestion
from app.schemas.gestion import GestionPageResponse, GestionRequest, GestionResponse

router = APIRouter(tags=["gestion"])
router_convocatorias = APIRouter(tags=["gestion"])


@router_convocatorias.put(
    "/{convocatoria_id}/gestion",
    response_model=GestionResponse,
    summary="Marca una convocatoria como postulada o descartada",
)
def marcar(
    convocatoria_id: int,
    payload: GestionRequest,
    db: Session = Depends(get_db),
) -> GestionResponse:
    """Upsert de la marca. 404 si la convocatoria no existe."""
    gestion = service.marcar(db, convocatoria_id, payload)
    if gestion is None:
        raise HTTPException(status_code=404, detail="Convocatoria no encontrada")
    return gestion


@router_convocatorias.delete(
    "/{convocatoria_id}/gestion",
    status_code=204,
    summary="Quita la marca de gestión (la convocatoria vuelve al listado)",
)
def desmarcar(convocatoria_id: int, db: Session = Depends(get_db)) -> Response:
    """204 si se borró; 404 si la convocatoria no tenía marca."""
    if not service.desmarcar(db, convocatoria_id):
        raise HTTPException(status_code=404, detail="Gestión no encontrada")
    return Response(status_code=204)


@router.get(
    "",
    response_model=GestionPageResponse,
    summary="Histórico paginado de convocatorias gestionadas",
)
def listar(
    estado_gestion: EstadoGestion | None = Query(
        None, description="Filtra por 'postulada' o 'descartada'."
    ),
    responsable: str | None = Query(None, description="Responsable exacto."),
    paginacion: PaginacionParams = Depends(),
    db: Session = Depends(get_db),
) -> GestionPageResponse:
    """Histórico con la convocatoria embebida (más reciente primero)."""
    return service.listar(db, estado_gestion, responsable, paginacion)
