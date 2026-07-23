"""apto_fundaciones_nuevas: flag derivado para fundaciones nuevas/primerizas

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-23

Añade la columna booleana `apto_fundaciones_nuevas` (NOT NULL, default false) y su
índice. Es un flag DERIVADO que calcula el pipeline desde el contenido real
(ver app.pipeline.normalizer + app.constants); no es un dato de la fuente.
Debe coincidir 1:1 con el modelo app.models.convocatoria.
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "convocatorias",
        sa.Column(
            "apto_fundaciones_nuevas",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_convocatorias_apto_fundaciones_nuevas",
        "convocatorias",
        ["apto_fundaciones_nuevas"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_convocatorias_apto_fundaciones_nuevas", table_name="convocatorias"
    )
    op.drop_column("convocatorias", "apto_fundaciones_nuevas")
