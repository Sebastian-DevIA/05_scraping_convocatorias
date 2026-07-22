"""Consulta de fuentes y su historial de ejecuciones.

`listar_fuentes` embebe la última ejecución de cada fuente resolviéndola con un
`DISTINCT ON (fuente_id) ... ORDER BY fuente_id, inicio DESC` (una sola query
extra, sin N+1).
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.ejecucion import Ejecucion
from app.models.fuente import Fuente
from app.schemas.ejecucion import EjecucionListResponse, EjecucionResponse
from app.schemas.fuente import FuenteListResponse, FuenteResponse


def _a_fuente_response(f: Fuente, ultima: Ejecucion | None) -> FuenteResponse:
    return FuenteResponse(
        id=f.id,
        codigo=f.codigo,
        nombre=f.nombre,
        url_base=f.url_base,
        tipo=f.tipo,
        activa=f.activa,
        config=f.config,
        creado_en=f.creado_en,
        actualizado_en=f.actualizado_en,
        ultima_ejecucion=EjecucionResponse.model_validate(ultima) if ultima else None,
    )


def listar_fuentes(db: Session) -> FuenteListResponse:
    """Todas las fuentes con su última ejecución embebida (salud del conector)."""
    fuentes = db.execute(select(Fuente).order_by(Fuente.id)).scalars().all()

    # Última ejecución por fuente en una sola pasada (DISTINCT ON de Postgres).
    ultimas = (
        db.execute(
            select(Ejecucion)
            .order_by(Ejecucion.fuente_id, Ejecucion.inicio.desc())
            .distinct(Ejecucion.fuente_id)
        )
        .scalars()
        .all()
    )
    ultima_por_fuente = {e.fuente_id: e for e in ultimas}

    items = [_a_fuente_response(f, ultima_por_fuente.get(f.id)) for f in fuentes]
    return FuenteListResponse(items=items, total=len(items))


def obtener_fuente_por_codigo(db: Session, codigo: str) -> Fuente | None:
    """Fuente por su `codigo` (None si no existe)."""
    return db.execute(
        select(Fuente).where(Fuente.codigo == codigo)
    ).scalar_one_or_none()


def listar_ejecuciones(db: Session, fuente: Fuente, limit: int) -> EjecucionListResponse:
    """Historial de ejecuciones de una fuente (más recientes primero).

    `total` es el histórico completo; `items` está acotado por `limit`.
    """
    total = db.execute(
        select(func.count())
        .select_from(Ejecucion)
        .where(Ejecucion.fuente_id == fuente.id)
    ).scalar_one()

    filas = (
        db.execute(
            select(Ejecucion)
            .where(Ejecucion.fuente_id == fuente.id)
            .order_by(Ejecucion.inicio.desc())
            .limit(limit)
        )
        .scalars()
        .all()
    )

    return EjecucionListResponse(
        items=[EjecucionResponse.model_validate(e) for e in filas],
        total=total,
    )
