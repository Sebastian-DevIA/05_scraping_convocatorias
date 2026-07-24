"""gestiones (histórico propio de postulaciones) + convocatorias.ambito

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-23

Dos cambios cohesivos:

1. Tabla `gestiones`: registro NUESTRO de a qué convocatorias nos postulamos
   (o cuáles descartamos) con este software, para que dejen de aparecer en la
   búsqueda. Va en tabla aparte porque el upsert del pipeline reescribe las
   columnas de `convocatorias` en cada scraping. Ver app.models.gestion.
2. Columna `convocatorias.ambito` (nacional|territorial|internacional|
   desconocido): la mapea el pipeline desde el `ambito_fuente` crudo (ej. el
   `ordenentidad` de SECOP II) y permite filtrar convocatorias de alcaldías y
   gobernaciones. Se añade también el índice de `ciudad` que faltaba, para que
   el filtro por ciudad no haga seq scan.

Debe coincidir 1:1 con los modelos app.models.convocatoria y app.models.gestion.
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- 1. convocatorias.ambito ------------------------------------------
    op.add_column(
        "convocatorias",
        sa.Column(
            "ambito",
            sa.String(length=20),
            server_default="desconocido",
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "ck_convocatorias_ambito",
        "convocatorias",
        "ambito IN ('nacional', 'territorial', 'internacional', 'desconocido')",
    )
    op.create_index("ix_convocatorias_ambito", "convocatorias", ["ambito"])
    op.create_index("ix_convocatorias_ciudad", "convocatorias", ["ciudad"])

    # --- 2. gestiones ------------------------------------------------------
    op.create_table(
        "gestiones",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("convocatoria_id", sa.Integer(), nullable=False),
        sa.Column("estado_gestion", sa.String(length=20), nullable=False),
        sa.Column("responsable", sa.String(length=120), nullable=True),
        sa.Column("fecha_postulacion", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notas", sa.Text(), nullable=True),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "actualizado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["convocatoria_id"], ["convocatorias.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("convocatoria_id"),
        sa.CheckConstraint(
            "estado_gestion IN ('postulada', 'descartada')",
            name="ck_gestiones_estado_gestion",
        ),
    )
    op.create_index("ix_gestiones_estado_gestion", "gestiones", ["estado_gestion"])
    op.create_index("ix_gestiones_responsable", "gestiones", ["responsable"])


def downgrade() -> None:
    op.drop_index("ix_gestiones_responsable", table_name="gestiones")
    op.drop_index("ix_gestiones_estado_gestion", table_name="gestiones")
    op.drop_table("gestiones")

    op.drop_index("ix_convocatorias_ciudad", table_name="convocatorias")
    op.drop_index("ix_convocatorias_ambito", table_name="convocatorias")
    op.drop_constraint("ck_convocatorias_ambito", "convocatorias", type_="check")
    op.drop_column("convocatorias", "ambito")
