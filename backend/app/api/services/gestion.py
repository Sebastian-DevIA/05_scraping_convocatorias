"""Lógica del histórico propio de gestión (a qué convocatorias nos postulamos).

A diferencia del resto de servicios, aquí se ESCRIBEN datos NUESTROS (no de las
fuentes): la marca `postulada`/`descartada` de cada convocatoria. Las marcadas
salen del listado de búsqueda (ver `app.api.services.convocatorias`).

`SessionLocal` usa `autoflush=False` -> se llama `db.flush()` antes de leer el
objeto recién añadido/borrado. `get_db` no hace commit: lo hace este servicio.
"""

from datetime import datetime, timezone

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import PaginacionParams
from app.api.services.convocatorias import a_convocatoria_response
from app.constants import EstadoGestion
from app.models.convocatoria import Convocatoria
from app.models.gestion import Gestion
from app.schemas.gestion import (
    GestionItemResponse,
    GestionPageResponse,
    GestionRequest,
    GestionResponse,
)


def _obtener(db: Session, convocatoria_id: int) -> Gestion | None:
    """Marca de gestión de una convocatoria (0 o 1 por la UNIQUE de la tabla)."""
    return db.execute(
        select(Gestion).where(Gestion.convocatoria_id == convocatoria_id)
    ).scalar_one_or_none()


def _fecha_postulacion(payload: GestionRequest) -> datetime | None:
    """Solo aplica a `postulada`; si no viene, es "ahora" (UTC). Nunca inventar
    una fecha para `descartada`: queda NULL."""
    if payload.estado_gestion != "postulada":
        return None
    return payload.fecha_postulacion or datetime.now(timezone.utc)


def marcar(
    db: Session, convocatoria_id: int, payload: GestionRequest
) -> GestionResponse | None:
    """Upsert de la marca de gestión. None si la convocatoria no existe."""
    if db.get(Convocatoria, convocatoria_id) is None:
        return None

    gestion = _obtener(db, convocatoria_id)
    if gestion is None:
        gestion = Gestion(convocatoria_id=convocatoria_id)
        db.add(gestion)

    gestion.estado_gestion = payload.estado_gestion
    gestion.responsable = payload.responsable
    gestion.notas = payload.notas
    gestion.fecha_postulacion = _fecha_postulacion(payload)

    db.flush()  # autoflush=False: fuerza el INSERT/UPDATE antes de leer defaults.
    db.commit()
    db.refresh(gestion)
    return GestionResponse.model_validate(gestion)


def desmarcar(db: Session, convocatoria_id: int) -> bool:
    """Borra la marca (la convocatoria vuelve al listado). False si no había."""
    gestion = _obtener(db, convocatoria_id)
    if gestion is None:
        return False

    db.delete(gestion)
    db.flush()
    db.commit()
    return True


def listar(
    db: Session,
    estado_gestion: EstadoGestion | None,
    responsable: str | None,
    paginacion: PaginacionParams,
) -> GestionPageResponse:
    """Histórico paginado con la convocatoria embebida (más reciente primero)."""
    condiciones: list[ColumnElement[bool]] = []
    if estado_gestion:
        condiciones.append(Gestion.estado_gestion == estado_gestion)
    if responsable:
        condiciones.append(Gestion.responsable == responsable)

    total = db.execute(
        select(func.count()).select_from(Gestion).where(*condiciones)
    ).scalar_one()

    filas = (
        db.execute(
            select(Gestion)
            .options(
                joinedload(Gestion.convocatoria).joinedload(Convocatoria.fuente),
                # La propia marca, que `a_convocatoria_response` lee para
                # rellenar `estado_gestion` (evita el N+1 del lazy load).
                joinedload(Gestion.convocatoria).joinedload(Convocatoria.gestion),
            )
            .where(*condiciones)
            .order_by(Gestion.actualizado_en.desc(), Gestion.id.desc())
            .offset(paginacion.offset)
            .limit(paginacion.limit)
        )
        .scalars()
        .all()
    )

    items = [
        GestionItemResponse(
            **GestionResponse.model_validate(g).model_dump(),
            convocatoria=a_convocatoria_response(g.convocatoria),
        )
        for g in filas
    ]

    return GestionPageResponse(
        items=items,
        total=total,
        page=paginacion.page,
        page_size=paginacion.page_size,
    )
