"""esquema inicial: fuentes, convocatorias, ejecuciones

Revision ID: 0001
Revises:
Create Date: 2026-07-21

Debe coincidir 1:1 con los modelos de app.models. Incluye la columna GENERADA
`busqueda` (tsvector 'spanish' sobre titulo+descripcion) y su índice GIN.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Expresión del tsvector generado (idéntica a app.models.convocatoria).
_BUSQUEDA_EXPR = (
    "to_tsvector('spanish', "
    "coalesce(titulo, '') || ' ' || coalesce(descripcion, ''))"
)


def upgrade() -> None:
    # --- fuentes -----------------------------------------------------------
    op.create_table(
        "fuentes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("codigo", sa.String(length=50), nullable=False),
        sa.Column("nombre", sa.String(length=200), nullable=False),
        sa.Column("url_base", sa.String(length=500), nullable=False),
        sa.Column("tipo", sa.String(length=10), nullable=False),
        sa.Column("activa", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "config",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_fuentes"),
        sa.UniqueConstraint("codigo", name="uq_fuentes_codigo"),
        sa.CheckConstraint("tipo IN ('api', 'html', 'js')", name="ck_fuentes_tipo"),
    )

    # --- convocatorias -----------------------------------------------------
    op.create_table(
        "convocatorias",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("fuente_id", sa.Integer(), nullable=False),
        sa.Column("id_externo", sa.String(length=255), nullable=False),
        sa.Column("hash_dedupe", sa.String(length=64), nullable=False),
        sa.Column("hash_contenido", sa.String(length=64), nullable=False),
        sa.Column("titulo", sa.Text(), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("entidad", sa.String(length=500), nullable=True),
        sa.Column("tipo", sa.String(length=20), nullable=False),
        sa.Column("modalidad", sa.String(length=200), nullable=True),
        sa.Column("estado", sa.String(length=20), server_default=sa.text("'desconocido'"), nullable=False),
        sa.Column("monto", sa.Numeric(precision=20, scale=2), nullable=True),
        sa.Column("moneda", sa.String(length=10), nullable=True),
        sa.Column("departamento", sa.String(length=120), nullable=True),
        sa.Column("ciudad", sa.String(length=120), nullable=True),
        sa.Column("pais", sa.String(length=120), server_default=sa.text("'Colombia'"), nullable=False),
        sa.Column("fecha_publicacion", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fecha_apertura", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fecha_cierre", sa.DateTime(timezone=True), nullable=True),
        sa.Column("requisitos", sa.Text(), nullable=True),
        sa.Column("url_original", sa.Text(), nullable=False),
        sa.Column(
            "keywords_match",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("'{}'::text[]"),
            nullable=False,
        ),
        sa.Column(
            "raw",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("primera_vez_visto", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("ultima_vez_visto", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column(
            "busqueda",
            postgresql.TSVECTOR(),
            sa.Computed(_BUSQUEDA_EXPR, persisted=True),
            nullable=True,
        ),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_convocatorias"),
        sa.ForeignKeyConstraint(
            ["fuente_id"], ["fuentes.id"], name="fk_convocatorias_fuente_id", ondelete="CASCADE"
        ),
        sa.UniqueConstraint("hash_dedupe", name="uq_convocatorias_hash_dedupe"),
        sa.UniqueConstraint("fuente_id", "id_externo", name="uq_convocatorias_fuente_id_externo"),
        sa.CheckConstraint(
            "estado IN ('abierta', 'cerrada', 'adjudicada', 'vencida', 'desconocido')",
            name="ck_convocatorias_estado",
        ),
        sa.CheckConstraint(
            "tipo IN ('licitacion', 'subvencion', 'fondo', 'rfp', 'eoi', 'otro')",
            name="ck_convocatorias_tipo",
        ),
    )
    op.create_index("ix_convocatorias_estado", "convocatorias", ["estado"])
    op.create_index("ix_convocatorias_fecha_cierre", "convocatorias", ["fecha_cierre"])
    op.create_index(
        "ix_convocatorias_fecha_publicacion",
        "convocatorias",
        [sa.text("fecha_publicacion DESC")],
    )
    op.create_index("ix_convocatorias_departamento", "convocatorias", ["departamento"])
    op.create_index(
        "ix_convocatorias_busqueda", "convocatorias", ["busqueda"], postgresql_using="gin"
    )

    # --- ejecuciones -------------------------------------------------------
    op.create_table(
        "ejecuciones",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("fuente_id", sa.Integer(), nullable=False),
        sa.Column("trigger", sa.String(length=10), nullable=False),
        sa.Column("inicio", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("fin", sa.DateTime(timezone=True), nullable=True),
        sa.Column("estado", sa.String(length=10), server_default=sa.text("'en_curso'"), nullable=False),
        sa.Column("items_obtenidos", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("items_nuevos", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("items_actualizados", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("items_marcados_cerrados", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("error_mensaje", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_ejecuciones"),
        sa.ForeignKeyConstraint(
            ["fuente_id"], ["fuentes.id"], name="fk_ejecuciones_fuente_id", ondelete="CASCADE"
        ),
        sa.CheckConstraint("trigger IN ('cron', 'manual')", name="ck_ejecuciones_trigger"),
        sa.CheckConstraint(
            "estado IN ('en_curso', 'ok', 'parcial', 'error')", name="ck_ejecuciones_estado"
        ),
    )
    op.create_index(
        "ix_ejecuciones_fuente_inicio",
        "ejecuciones",
        ["fuente_id", sa.text("inicio DESC")],
    )


def downgrade() -> None:
    op.drop_index("ix_ejecuciones_fuente_inicio", table_name="ejecuciones")
    op.drop_table("ejecuciones")

    op.drop_index("ix_convocatorias_busqueda", table_name="convocatorias")
    op.drop_index("ix_convocatorias_departamento", table_name="convocatorias")
    op.drop_index("ix_convocatorias_fecha_publicacion", table_name="convocatorias")
    op.drop_index("ix_convocatorias_fecha_cierre", table_name="convocatorias")
    op.drop_index("ix_convocatorias_estado", table_name="convocatorias")
    op.drop_table("convocatorias")

    op.drop_table("fuentes")
