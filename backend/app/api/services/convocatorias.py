"""Lógica de consulta de convocatorias: listado con filtros y detalle.

La forma exacta de la respuesta está congelada en `docs/api-contract.md`.
`fuente_codigo`/`fuente_nombre` se componen aquí a partir del join con `fuentes`
(joinedload, sin N+1). El full-text usa la columna generada `busqueda`
(tsvector español) con `websearch_to_tsquery('spanish', q)`.
"""

from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import ConvocatoriaFiltros, PaginacionParams
from app.models.convocatoria import Convocatoria
from app.models.fuente import Fuente
from app.schemas.convocatoria import (
    ConvocatoriaDetailResponse,
    ConvocatoriaPageResponse,
    ConvocatoriaResponse,
)

# Campo de orden admitido -> columna real de la tabla.
_ORDEN_COLUMNAS = {
    "fecha_publicacion": Convocatoria.fecha_publicacion,
    "fecha_cierre": Convocatoria.fecha_cierre,
    "monto": Convocatoria.monto,
    "ultima_vez_visto": Convocatoria.ultima_vez_visto,
}


def _inicio_dia(dia: date) -> datetime:
    """Medianoche UTC del día dado (los timestamps de dominio son TIMESTAMPTZ)."""
    return datetime.combine(dia, time.min, tzinfo=timezone.utc)


def _construir_condiciones(f: ConvocatoriaFiltros) -> list[ColumnElement[bool]]:
    """Traduce los filtros del contrato a condiciones WHERE de SQLAlchemy."""
    condiciones: list[ColumnElement[bool]] = []

    if f.q:
        # Full-text en español contra la columna generada `busqueda` (tsvector).
        condiciones.append(
            Convocatoria.busqueda.bool_op("@@")(func.websearch_to_tsquery("spanish", f.q))
        )
    if f.fuente:
        # Código inexistente -> subquery vacía -> 0 resultados (sin 404 en el listado).
        condiciones.append(
            Convocatoria.fuente_id.in_(select(Fuente.id).where(Fuente.codigo == f.fuente))
        )
    if f.estado:
        condiciones.append(Convocatoria.estado == f.estado)
    if f.tipo:
        condiciones.append(Convocatoria.tipo == f.tipo)
    if f.departamento:
        condiciones.append(Convocatoria.departamento == f.departamento)

    if f.fecha_publicacion_desde:
        condiciones.append(Convocatoria.fecha_publicacion >= _inicio_dia(f.fecha_publicacion_desde))
    if f.fecha_publicacion_hasta:
        # `hasta` inclusivo del día completo: < medianoche del día siguiente.
        condiciones.append(
            Convocatoria.fecha_publicacion < _inicio_dia(f.fecha_publicacion_hasta + timedelta(days=1))
        )
    if f.fecha_cierre_desde:
        condiciones.append(Convocatoria.fecha_cierre >= _inicio_dia(f.fecha_cierre_desde))
    if f.fecha_cierre_hasta:
        condiciones.append(
            Convocatoria.fecha_cierre < _inicio_dia(f.fecha_cierre_hasta + timedelta(days=1))
        )

    if f.monto_min is not None:
        condiciones.append(Convocatoria.monto >= f.monto_min)
    if f.monto_max is not None:
        condiciones.append(Convocatoria.monto <= f.monto_max)

    return condiciones


def _order_by(orden: str) -> list:
    """`orden` validado por el patrón del contrato. `-campo` = descendente.

    Se añade `id DESC` como desempate para una paginación estable.
    """
    descendente = orden.startswith("-")
    campo = orden[1:] if descendente else orden
    columna = _ORDEN_COLUMNAS[campo]
    principal = columna.desc() if descendente else columna.asc()
    return [principal, Convocatoria.id.desc()]


def _a_response(c: Convocatoria) -> ConvocatoriaResponse:
    """Modelo ORM (con `fuente` cargada) -> schema de listado."""
    return ConvocatoriaResponse(
        id=c.id,
        id_externo=c.id_externo,
        fuente_id=c.fuente_id,
        fuente_codigo=c.fuente.codigo,
        fuente_nombre=c.fuente.nombre,
        titulo=c.titulo,
        descripcion=c.descripcion,
        entidad=c.entidad,
        tipo=c.tipo,
        modalidad=c.modalidad,
        estado=c.estado,
        monto=c.monto,
        moneda=c.moneda,
        departamento=c.departamento,
        ciudad=c.ciudad,
        pais=c.pais,
        fecha_publicacion=c.fecha_publicacion,
        fecha_apertura=c.fecha_apertura,
        fecha_cierre=c.fecha_cierre,
        url_original=c.url_original,
        keywords_match=list(c.keywords_match or []),
        primera_vez_visto=c.primera_vez_visto,
        ultima_vez_visto=c.ultima_vez_visto,
        creado_en=c.creado_en,
        actualizado_en=c.actualizado_en,
    )


def _a_detail_response(c: Convocatoria, include_raw: bool) -> ConvocatoriaDetailResponse:
    """Añade `requisitos` y `raw` (solo si `include_raw`) al schema de detalle."""
    base = _a_response(c)
    return ConvocatoriaDetailResponse(
        **base.model_dump(),
        requisitos=c.requisitos,
        raw=c.raw if include_raw else None,
    )


def listar_convocatorias(
    db: Session, filtros: ConvocatoriaFiltros, paginacion: PaginacionParams
) -> ConvocatoriaPageResponse:
    """Listado paginado con filtros -> `{items, total, page, page_size}`."""
    condiciones = _construir_condiciones(filtros)

    total = db.execute(
        select(func.count()).select_from(Convocatoria).where(*condiciones)
    ).scalar_one()

    filas = (
        db.execute(
            select(Convocatoria)
            .options(joinedload(Convocatoria.fuente))
            .where(*condiciones)
            .order_by(*_order_by(filtros.orden))
            .offset(paginacion.offset)
            .limit(paginacion.limit)
        )
        .scalars()
        .all()
    )

    return ConvocatoriaPageResponse(
        items=[_a_response(c) for c in filas],
        total=total,
        page=paginacion.page,
        page_size=paginacion.page_size,
    )


def obtener_convocatoria(
    db: Session, convocatoria_id: int, include_raw: bool
) -> ConvocatoriaDetailResponse | None:
    """Detalle por id (con `requisitos`, y `raw` si `include_raw`). None si no existe."""
    convocatoria = db.execute(
        select(Convocatoria)
        .options(joinedload(Convocatoria.fuente))
        .where(Convocatoria.id == convocatoria_id)
    ).scalar_one_or_none()

    if convocatoria is None:
        return None
    return _a_detail_response(convocatoria, include_raw)
