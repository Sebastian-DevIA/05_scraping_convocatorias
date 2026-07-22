"""Modelo `fuentes`: catálogo de conectores/fuentes de convocatorias."""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.constants import TIPOS_FUENTE
from app.database import Base


class Fuente(Base):
    __tablename__ = "fuentes"
    __table_args__ = (
        CheckConstraint(
            "tipo IN ('api', 'html', 'js')",
            name="ck_fuentes_tipo",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    # Identificador estable del conector: secop|pnud|minciencias|mintic|ungm.
    codigo: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    url_base: Mapped[str] = mapped_column(String(500), nullable=False)

    # Tipo de acceso: api | html | js (ver TIPOS_FUENTE).
    tipo: Mapped[str] = mapped_column(String(10), nullable=False)

    # ungm arranca en false (stub, carga por JS).
    activa: Mapped[bool] = mapped_column(nullable=False, default=True, server_default="true")

    # Config del conector: keywords, max_paginas, rate_limit_seconds, etc.
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict, server_default="{}")

    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    convocatorias: Mapped[list["Convocatoria"]] = relationship(  # noqa: F821
        back_populates="fuente"
    )
    ejecuciones: Mapped[list["Ejecucion"]] = relationship(  # noqa: F821
        back_populates="fuente"
    )

    # Referencia estática para documentación / validación externa.
    TIPOS = TIPOS_FUENTE

    def __repr__(self) -> str:  # pragma: no cover - ayuda de depuración
        return f"<Fuente {self.codigo} activa={self.activa}>"
