"""Router de convocatorias. `GET /convocatorias` (listado), `/{id}` (detalle) y
`POST /convocatorias/export` (descarga a Excel de las seleccionadas)."""

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.api.deps import ConvocatoriaFiltros, PaginacionParams, get_db
from app.api.services import convocatorias as service
from app.schemas.convocatoria import (
    ConvocatoriaDetailResponse,
    ConvocatoriaExportRequest,
    ConvocatoriaPageResponse,
)

router = APIRouter(tags=["convocatorias"])

_XLSX_MEDIA = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


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


@router.post(
    "/export",
    summary="Exporta a Excel (.xlsx) las convocatorias seleccionadas",
    responses={200: {"content": {_XLSX_MEDIA: {}}, "description": "Archivo .xlsx"}},
)
def exportar_excel(
    payload: ConvocatoriaExportRequest,
    db: Session = Depends(get_db),
) -> Response:
    """Recibe los ids seleccionados y devuelve un `.xlsx` con los datos para
    participar (incluye `url_original` para verificar que la convocatoria existe).
    """
    contenido = service.exportar_convocatorias_excel(db, payload.ids)
    return Response(
        content=contenido,
        media_type=_XLSX_MEDIA,
        headers={
            "Content-Disposition": (
                'attachment; filename="convocatorias_seleccionadas.xlsx"'
            )
        },
    )


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
