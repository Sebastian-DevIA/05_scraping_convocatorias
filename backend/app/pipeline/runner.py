"""Runner de scraping: fuente -> conector -> normalización -> upsert."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import func, select, text

from app.connectors import ConnectorError, get_connector
from app.database import SessionLocal
from app.models.ejecucion import Ejecucion
from app.models.fuente import Fuente
from app.pipeline.normalizer import normalizar
from app.pipeline.upsert import upsert_convocatorias

logger = logging.getLogger(__name__)
LOCK_KEY = 2026072106


def _fuentes(db, codigo: str | None) -> list[Fuente]:
    stmt = select(Fuente).order_by(Fuente.id)
    if codigo:
        stmt = stmt.where(Fuente.codigo == codigo)
    else:
        stmt = stmt.where(Fuente.activa.is_(True))
    return list(db.execute(stmt).scalars().all())


def run(fuente: str | None = None, trigger: str = "manual") -> None:
    """Ejecuta scraping para una fuente o todas las activas."""
    db = SessionLocal()
    try:
        locked = db.execute(text("SELECT pg_try_advisory_lock(:key)"), {"key": LOCK_KEY}).scalar_one()
        if not locked:
            logger.info("Scraping omitido: ya hay una corrida en curso")
            return
        try:
            for fuente_db in _fuentes(db, fuente):
                ejecucion = Ejecucion(fuente_id=fuente_db.id, trigger=trigger, estado="en_curso")
                db.add(ejecucion)
                db.flush()
                try:
                    connector = get_connector(fuente_db.codigo)
                    if connector is None:
                        raise ConnectorError(f"No hay conector registrado para {fuente_db.codigo}")
                    raw_items = connector.fetch(fuente_db.config or {})
                    keywords = (fuente_db.config or {}).get("keywords") or []
                    items = [normalizar(raw, fuente_db.codigo, keywords) for raw in raw_items]
                    conteo = upsert_convocatorias(db, fuente_db.id, items)
                    ejecucion.items_obtenidos = len(raw_items)
                    ejecucion.items_nuevos = conteo.nuevos
                    ejecucion.items_actualizados = conteo.actualizados
                    ejecucion.estado = "ok"
                except Exception as exc:  # noqa: BLE001 - aísla cada fuente
                    logger.exception("Error ejecutando fuente %s", fuente_db.codigo)
                    ejecucion.estado = "error"
                    ejecucion.error_mensaje = str(exc)[:4000]
                finally:
                    ejecucion.fin = datetime.now(timezone.utc)
                    db.commit()
        finally:
            db.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": LOCK_KEY})
            db.commit()
    finally:
        db.close()


def fuente_existe(codigo: str) -> bool:
    db = SessionLocal()
    try:
        return db.execute(select(func.count()).select_from(Fuente).where(Fuente.codigo == codigo)).scalar_one() > 0
    finally:
        db.close()
