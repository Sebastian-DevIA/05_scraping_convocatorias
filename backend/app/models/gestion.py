"""Modelo `gestiones`: histórico propio de postulaciones.

A diferencia de `convocatorias` (datos REALES traídos de las fuentes), esta
tabla guarda datos NUESTROS: a qué convocatorias nos postulamos con este
software y cuáles descartamos, para que dejen de aparecer en la búsqueda y no
se repita una postulación.

Va en tabla aparte a propósito: el upsert del pipeline
(`app.pipeline.upsert.upsert_convocatorias`) reescribe todas las columnas de
`convocatorias` cuando cambia `hash_contenido`, así que una marca guardada allí
se perdería en el siguiente scraping.

Sin login: una instalación = una organización. `responsable` es texto libre
para saber quién del equipo hizo la marca.
"""

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.constants import ESTADOS_GESTION
from app.database import Base


class Gestion(Base):
    __tablename__ = "gestiones"
    __table_args__ = (
        CheckConstraint(
            "estado_gestion IN ('en_seguimiento', 'postulada', 'descartada')",
            name="ck_gestiones_estado_gestion",
        ),
        Index("ix_gestiones_estado_gestion", "estado_gestion"),
        Index("ix_gestiones_responsable", "responsable"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    # UNIQUE: 0 o 1 registro de gestión por convocatoria.
    convocatoria_id: Mapped[int] = mapped_column(
        ForeignKey("convocatorias.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    # Estado canónico: postulada|descartada. Ambos salen de la búsqueda.
    estado_gestion: Mapped[str] = mapped_column(String(20), nullable=False)

    # Quién del equipo marcó el registro (texto libre, sin login). None si no se indicó.
    responsable: Mapped[str | None] = mapped_column(String(120), nullable=True)

    # Cuándo nos postulamos (UTC). Solo aplica a `postulada`; en los demás es NULL.
    fecha_postulacion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    notas: Mapped[str | None] = mapped_column(Text, nullable=True)

    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    convocatoria: Mapped["Convocatoria"] = relationship(  # noqa: F821
        back_populates="gestion"
    )

    # Referencia estática para documentación / validación externa.
    ESTADOS = ESTADOS_GESTION

    def __repr__(self) -> str:  # pragma: no cover - ayuda de depuración
        return f"<Gestion conv={self.convocatoria_id} estado={self.estado_gestion}>"
