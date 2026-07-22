"""Router de convocatorias. `GET /convocatorias` (listado) y `/{id}` (detalle)."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import ConvocatoriaFiltros, PaginacionParams, get_db
from app.api.services import convocatorias as service
from app.schemas.convocatoria import ConvocatoriaDetailResponse, ConvocatoriaPageResponse

router = APIRouter(tags=["convocatorias"])


@router.get(
    "",
    response_model=ConvocatoriaPageResponse,
    summary="Listado paginado de convocatorias con filtros",
)
def listar(
    filtros: ConvocatoriaFiltros = Depends(),
    paginacion: PaginacionParams = Depends(),
    db: Session = Depends(get_db),
) -> ConvocatoriaPageResponse:
    """Listado paginado. Ver filtros y orden en `docs/api-contract.md`."""
    return service.listar_convocatorias(db, filtros, paginacion)


@router.get(
    "/{convocatoria_id}",
    response_model=ConvocatoriaDetailResponse,
    summary="Detalle de una convocatoria",
)
def detalle(
    convocatoria_id: int,
    include_raw: bool = Query(
        False, description="Si es true, incluye `raw` (payload íntegro de la fuente)."
    ),
    db: Session = Depends(get_db),
) -> ConvocatoriaDetailResponse:
    """Detalle con `requisitos`. `?include_raw=true` añade `raw`. 404 si no existe."""
    convocatoria = service.obtener_convocatoria(db, convocatoria_id, include_raw)
    if convocatoria is None:
        raise HTTPException(status_code=404, detail="Convocatoria no encontrada")
    return convocatoria
