"""Router de fuentes y ejecuciones."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.services import fuentes as service
from app.schemas.ejecucion import EjecucionListResponse
from app.schemas.fuente import FuenteListResponse

router = APIRouter(tags=["fuentes"])


@router.get("", response_model=FuenteListResponse)
def listar(db: Session = Depends(get_db)) -> FuenteListResponse:
    return service.listar_fuentes(db)


@router.get("/{codigo}/ejecuciones", response_model=EjecucionListResponse)
def ejecuciones(
    codigo: str,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> EjecucionListResponse:
    fuente = service.obtener_fuente_por_codigo(db, codigo)
    if fuente is None:
        raise HTTPException(status_code=404, detail="Fuente no encontrada")
    return service.listar_ejecuciones(db, fuente, limit)
