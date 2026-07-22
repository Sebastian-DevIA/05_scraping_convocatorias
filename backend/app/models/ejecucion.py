"""Modelo `ejecuciones`: bitácora de cada corrida de un conector."""

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.constants import ESTADOS_EJECUCION, TRIGGERS_EJECUCION
from app.database import Base


class Ejecucion(Base):
    __tablename__ = "ejecuciones"
    __table_args__ = (
        CheckConstraint(
            "trigger IN ('cron', 'manual')",
            name="ck_ejecuciones_trigger",
        ),
        CheckConstraint(
            "estado IN ('en_curso', 'ok', 'parcial', 'error')",
            name="ck_ejecuciones_estado",
        ),
        Index("ix_ejecuciones_fuente_inicio", "fuente_id", text("inicio DESC")),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    fuente_id: Mapped[int] = mapped_column(
        ForeignKey("fuentes.id", ondelete="CASCADE"), nullable=False
    )

    # Origen de la corrida: cron | manual.
    trigger: Mapped[str] = mapped_column(String(10), nullable=False)

    inicio: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    fin: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Estado de la corrida: en_curso | ok | parcial | error.
    estado: Mapped[str] = mapped_column(
        String(10), nullable=False, default="en_curso", server_default="en_curso"
    )

    items_obtenidos: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    items_nuevos: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    items_actualizados: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    items_marcados_cerrados: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )

    error_mensaje: Mapped[str | None] = mapped_column(Text, nullable=True)

    fuente: Mapped["Fuente"] = relationship(back_populates="ejecuciones")  # noqa: F821

    # Referencias estáticas para documentación / validación externa.
    ESTADOS = ESTADOS_EJECUCION
    TRIGGERS = TRIGGERS_EJECUCION

    def __repr__(self) -> str:  # pragma: no cover - ayuda de depuración
        return f"<Ejecucion fuente={self.fuente_id} estado={self.estado}>"
