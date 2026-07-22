"""Modelo `convocatorias`: cada oportunidad captada y normalizada."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Computed,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.constants import ESTADOS_CONVOCATORIA, PAIS_DEFAULT, TIPOS_CONVOCATORIA
from app.database import Base

# Expresión del tsvector generado (config 'spanish' sobre titulo + descripcion).
_BUSQUEDA_EXPR = (
    "to_tsvector('spanish', "
    "coalesce(titulo, '') || ' ' || coalesce(descripcion, ''))"
)


class Convocatoria(Base):
    __tablename__ = "convocatorias"
    __table_args__ = (
        UniqueConstraint("fuente_id", "id_externo", name="uq_convocatorias_fuente_id_externo"),
        CheckConstraint(
            "estado IN ('abierta', 'cerrada', 'adjudicada', 'vencida', 'desconocido')",
            name="ck_convocatorias_estado",
        ),
        CheckConstraint(
            "tipo IN ('licitacion', 'subvencion', 'fondo', 'rfp', 'eoi', 'otro')",
            name="ck_convocatorias_tipo",
        ),
        Index("ix_convocatorias_estado", "estado"),
        Index("ix_convocatorias_fecha_cierre", "fecha_cierre"),
        Index("ix_convocatorias_fecha_publicacion", text("fecha_publicacion DESC")),
        Index("ix_convocatorias_departamento", "departamento"),
        Index("ix_convocatorias_busqueda", "busqueda", postgresql_using="gin"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    fuente_id: Mapped[int] = mapped_column(
        ForeignKey("fuentes.id", ondelete="CASCADE"), nullable=False
    )

    # Identificador de la convocatoria dentro de su fuente (crudo).
    id_externo: Mapped[str] = mapped_column(String(255), nullable=False)

    # sha256("{codigo_fuente}:{id_externo}") — clave de deduplicación global.
    hash_dedupe: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    # sha256 de campos relevantes normalizados — detecta cambios reales de contenido.
    hash_contenido: Mapped[str] = mapped_column(String(64), nullable=False)

    titulo: Mapped[str] = mapped_column(Text, nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    entidad: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Tipo canónico: licitacion|subvencion|fondo|rfp|eoi|otro.
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    modalidad: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # Estado canónico: abierta|cerrada|adjudicada|vencida|desconocido.
    estado: Mapped[str] = mapped_column(
        String(20), nullable=False, default="desconocido", server_default="desconocido"
    )

    monto: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    moneda: Mapped[str | None] = mapped_column(String(10), nullable=True)

    departamento: Mapped[str | None] = mapped_column(String(120), nullable=True)
    ciudad: Mapped[str | None] = mapped_column(String(120), nullable=True)
    pais: Mapped[str] = mapped_column(
        String(120), nullable=False, default=PAIS_DEFAULT, server_default=PAIS_DEFAULT
    )

    # Timestamps de dominio en UTC (TIMESTAMPTZ). Imparseable -> NULL, nunca inventar.
    fecha_publicacion: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fecha_apertura: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fecha_cierre: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    requisitos: Mapped[str | None] = mapped_column(Text, nullable=True)
    # url_original SIEMPRE presente (regla dura: enlace a la publicación real).
    url_original: Mapped[str] = mapped_column(Text, nullable=False)

    # Trazabilidad del filtro por keywords.
    keywords_match: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, default=list, server_default="{}"
    )

    # Payload íntegro tal cual lo entregó la fuente (auditoría).
    raw: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict, server_default="{}")

    primera_vez_visto: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    ultima_vez_visto: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Columna GENERADA (STORED) para búsqueda full-text en español.
    busqueda: Mapped[str | None] = mapped_column(
        TSVECTOR,
        Computed(_BUSQUEDA_EXPR, persisted=True),
        nullable=True,
    )

    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    fuente: Mapped["Fuente"] = relationship(back_populates="convocatorias")  # noqa: F821

    # Referencias estáticas para documentación / validación externa.
    ESTADOS = ESTADOS_CONVOCATORIA
    TIPOS = TIPOS_CONVOCATORIA

    def __repr__(self) -> str:  # pragma: no cover - ayuda de depuración
        return f"<Convocatoria {self.id_externo} estado={self.estado}>"
