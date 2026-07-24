"""Métricas agregadas para el dashboard (`GET /stats`).

Consultas agregadas (GROUP BY), sin N+1. Las ventanas de 7 días se calculan
en Python (UTC) y se comparan contra las columnas TIMESTAMPTZ.
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.convocatoria import Convocatoria
from app.models.fuente import Fuente
from app.models.gestion import Gestion
from app.schemas.stats import Conteo, ConteoPorFuente, StatsResponse


def obtener_stats(db: Session) -> StatsResponse:
    """Total, abiertas, ventanas de 7 días y agrupaciones por fuente/estado/departamento."""
    ahora = datetime.now(timezone.utc)
    hace_7d = ahora - timedelta(days=7)
    en_7d = ahora + timedelta(days=7)

    total = db.execute(select(func.count()).select_from(Convocatoria)).scalar_one()

    abiertas = db.execute(
        select(func.count())
        .select_from(Convocatoria)
        .where(Convocatoria.estado == "abierta")
    ).scalar_one()

    # Nuevas: primera_vez_visto en los últimos 7 días.
    nuevas_7d = db.execute(
        select(func.count())
        .select_from(Convocatoria)
        .where(Convocatoria.primera_vez_visto >= hace_7d)
    ).scalar_one()

    # Cierran pronto: abiertas cuyo cierre cae en los próximos 7 días.
    cierran_7d = db.execute(
        select(func.count())
        .select_from(Convocatoria)
        .where(
            Convocatoria.estado == "abierta",
            Convocatoria.fecha_cierre >= ahora,
            Convocatoria.fecha_cierre <= en_7d,
        )
    ).scalar_one()

    # Gestión propia (histórico): a qué nos postulamos y qué seguimos.
    aplicadas = db.execute(
        select(func.count())
        .select_from(Gestion)
        .where(Gestion.estado_gestion == "postulada")
    ).scalar_one()
    en_seguimiento = db.execute(
        select(func.count())
        .select_from(Gestion)
        .where(Gestion.estado_gestion == "en_seguimiento")
    ).scalar_one()

    total_fuente = func.count(Convocatoria.id).label("total")
    por_fuente = db.execute(
        select(Fuente.codigo, Fuente.nombre, total_fuente)
        .join(Convocatoria, Convocatoria.fuente_id == Fuente.id)
        .group_by(Fuente.codigo, Fuente.nombre)
        .order_by(total_fuente.desc(), Fuente.codigo)
    ).all()

    total_estado = func.count().label("total")
    por_estado = db.execute(
        select(Convocatoria.estado, total_estado)
        .group_by(Convocatoria.estado)
        .order_by(total_estado.desc(), Convocatoria.estado)
    ).all()

    total_depto = func.count().label("total")
    por_departamento = db.execute(
        select(Convocatoria.departamento, total_depto)
        .where(Convocatoria.departamento.isnot(None))  # `clave` del schema es str no-nulo.
        .group_by(Convocatoria.departamento)
        .order_by(total_depto.desc(), Convocatoria.departamento)
    ).all()

    return StatsResponse(
        total=total,
        abiertas=abiertas,
        nuevas_7d=nuevas_7d,
        cierran_7d=cierran_7d,
        aplicadas=aplicadas,
        en_seguimiento=en_seguimiento,
        por_fuente=[
            ConteoPorFuente(codigo=codigo, nombre=nombre, total=t)
            for codigo, nombre, t in por_fuente
        ],
        por_estado=[Conteo(clave=clave, total=t) for clave, t in por_estado],
        por_departamento=[Conteo(clave=clave, total=t) for clave, t in por_departamento],
    )
