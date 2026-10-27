"""indice_unico_parcial_email_activos

Sustituye la restriccion UNIQUE(email, eliminado_en) por un indice unico
parcial sobre email WHERE eliminado_en IS NULL.

Motivo: en SQL, NULL != NULL, por lo que la restriccion compuesta
permitia dos usuarios ACTIVOS con el mismo email (ambos con
eliminado_en NULL). El indice parcial lo impide a nivel de base de
datos y sigue permitiendo reutilizar el email de usuarios con
soft delete.

Revision ID: b7f3a91c2d04
Revises: 1ebe2bc15e88
Create Date: 2026-10-16 11:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b7f3a91c2d04'
down_revision: str | Sequence[str] | None = '1ebe2bc15e88'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """
    Elimina la constraint compuesta y crea el indice unico parcial.

    El indice solo cubre filas con eliminado_en IS NULL (usuarios activos),
    de modo que los registros con soft delete quedan fuera de la unicidad.
    """
    with op.batch_alter_table('usuarios', recreate='always') as batch_op:
        batch_op.drop_constraint('uq_usuarios_email_eliminado_en', type_='unique')

    op.create_index(
        'ux_usuarios_email_activo',
        'usuarios',
        ['email'],
        unique=True,
        sqlite_where=sa.text('eliminado_en IS NULL'),
        postgresql_where=sa.text('eliminado_en IS NULL'),
    )


def downgrade() -> None:
    """Revierte a la restriccion compuesta (email, eliminado_en)."""
    op.drop_index('ux_usuarios_email_activo', table_name='usuarios')

    with op.batch_alter_table('usuarios', recreate='always') as batch_op:
        batch_op.create_unique_constraint(
            'uq_usuarios_email_eliminado_en', ['email', 'eliminado_en']
        )
