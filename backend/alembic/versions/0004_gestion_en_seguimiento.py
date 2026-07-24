"""gestiones: nuevo estado 'en_seguimiento' en el ciclo de gestión

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-24

Amplía el CHECK de `gestiones.estado_gestion` para admitir el estado nuevo
`en_seguimiento` (marcada para preparar/aprobar internamente, ANTES de aplicar),
además de los `postulada` y `descartada` existentes. Solo cambia la restricción;
no toca datos ni columnas. Debe coincidir 1:1 con app.models.gestion.
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("ck_gestiones_estado_gestion", "gestiones", type_="check")
    op.create_check_constraint(
        "ck_gestiones_estado_gestion",
        "gestiones",
        "estado_gestion IN ('en_seguimiento', 'postulada', 'descartada')",
    )


def downgrade() -> None:
    # Vuelve al conjunto anterior. Las filas 'en_seguimiento' (si las hubiera)
    # violarían el CHECK viejo: se pasan a 'descartada' antes de re-crearlo.
    op.execute(
        "UPDATE gestiones SET estado_gestion = 'descartada' "
        "WHERE estado_gestion = 'en_seguimiento'"
    )
    op.drop_constraint("ck_gestiones_estado_gestion", "gestiones", type_="check")
    op.create_check_constraint(
        "ck_gestiones_estado_gestion",
        "gestiones",
        "estado_gestion IN ('postulada', 'descartada')",
    )
