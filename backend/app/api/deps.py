"""Dependencias compartidas de la API.

`get_db` se re-exporta desde aquí para que los routers importen sus dependencias
desde un único lugar (`app.api.deps`). Fase 1 añade además las dependencias de
paginación y de filtros de `GET /convocatorias` (parseo de query params).
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from fastapi import Query

from app.constants import EstadoConvocatoria, TipoConvocatoria
from app.database import get_db  # re-export

__all__ = [
    "get_db",
    "PaginacionParams",
    "ConvocatoriaFiltros",
    "MAX_PAGE_SIZE",
]

MAX_PAGE_SIZE = 100
DEFAULT_PAGE_SIZE = 20

# Campos de orden admitidos por `GET /convocatorias` (prefijo `-` = descendente).
# El patrón valida el query param y produce un 422 estándar si no coincide.
ORDEN_PATTERN = r"^-?(fecha_publicacion|fecha_cierre|monto|ultima_vez_visto)$"
ORDEN_DEFAULT = "-fecha_publicacion"


@dataclass
class PaginacionParams:
    """Dependencia de paginación reutilizable (base 1).

    Uso en un router:
        def listar(p: PaginacionParams = Depends()):
            ...
    Expone además `offset`/`limit` para las queries.
    """

    page: int = Query(1, ge=1, description="Página (base 1).")
    page_size: int = Query(
        DEFAULT_PAGE_SIZE,
        ge=1,
        le=MAX_PAGE_SIZE,
        description=f"Tamaño de página (máx. {MAX_PAGE_SIZE}).",
    )

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


@dataclass
class ConvocatoriaFiltros:
    """Filtros de `GET /convocatorias` (todos opcionales). Ver `docs/api-contract.md`.

    Se consume como dependencia (`Depends()`); cada campo es un query param.
    La lógica de traducción a SQL vive en `app.api.services.convocatorias`.
    """

    q: str | None = Query(
        None, description="Búsqueda full-text (tsquery español) sobre título + descripción."
    )
    fuente: str | None = Query(None, description="Código de fuente (secop, pnud, ...).")
    estado: EstadoConvocatoria | None = Query(None, description="Estado canónico.")
    tipo: TipoConvocatoria | None = Query(None, description="Tipo canónico.")
    departamento: str | None = Query(None, description="Departamento exacto.")

    fecha_publicacion_desde: date | None = Query(
        None, description="Límite inferior de fecha_publicacion (YYYY-MM-DD, inclusive)."
    )
    fecha_publicacion_hasta: date | None = Query(
        None, description="Límite superior de fecha_publicacion (YYYY-MM-DD, día incluido)."
    )
    fecha_cierre_desde: date | None = Query(
        None, description="Límite inferior de fecha_cierre (YYYY-MM-DD, inclusive)."
    )
    fecha_cierre_hasta: date | None = Query(
        None, description="Límite superior de fecha_cierre (YYYY-MM-DD, día incluido)."
    )

    monto_min: Decimal | None = Query(None, description="Monto mínimo (inclusive).")
    monto_max: Decimal | None = Query(None, description="Monto máximo (inclusive).")

    orden: str = Query(
        ORDEN_DEFAULT,
        pattern=ORDEN_PATTERN,
        description=(
            "Campo de orden: fecha_publicacion (default), fecha_cierre, monto, "
            "ultima_vez_visto. Prefijo '-' = descendente. Default -fecha_publicacion."
        ),
    )
