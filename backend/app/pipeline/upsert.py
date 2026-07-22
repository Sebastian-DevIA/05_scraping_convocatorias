"""Upsert de convocatorias con detección de cambios por `hash_contenido`."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.convocatoria import Convocatoria


@dataclass
class UpsertResult:
    nuevos: int = 0
    actualizados: int = 0


def upsert_convocatorias(db: Session, fuente_id: int, items: list[dict]) -> UpsertResult:
    result = UpsertResult()
    for item in items:
        existente_hash = db.execute(
            select(Convocatoria.hash_contenido).where(
                Convocatoria.hash_dedupe == item["hash_dedupe"]
            )
        ).scalar_one_or_none()

        values = {"fuente_id": fuente_id, **item}
        stmt = insert(Convocatoria).values(**values)
        update_values = {
            key: getattr(stmt.excluded, key)
            for key in values
            if key not in {"fuente_id", "id_externo", "hash_dedupe"}
        }
        update_values["ultima_vez_visto"] = func.now()
        update_values["actualizado_en"] = func.now()
        stmt = stmt.on_conflict_do_update(
            index_elements=[Convocatoria.hash_dedupe],
            set_=update_values,
            where=Convocatoria.hash_contenido != stmt.excluded.hash_contenido,
        )
        db.execute(stmt)

        if existente_hash is None:
            result.nuevos += 1
        elif existente_hash != item["hash_contenido"]:
            result.actualizados += 1
        else:
            db.execute(
                Convocatoria.__table__.update()
                .where(Convocatoria.hash_dedupe == item["hash_dedupe"])
                .values(ultima_vez_visto=func.now())
            )
    return result
