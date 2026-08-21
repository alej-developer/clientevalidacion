"""refactorizar_unique_email_para_soft_delete

Cambia la restriccion unica de 'email' a la combinacion '(email, eliminado_en)'
para soportar soft delete: los usuarios borrados logicamente liberan su email.

Nota: Usa batch_alter_table requerido por SQLite para modificar constraints.

Revision ID: 1ebe2bc15e88
Revises: e2b3c42c9510
Create Date: 2026-08-21 13:22:15.026674

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1ebe2bc15e88'
down_revision: Union[str, Sequence[str], None] = 'e2b3c42c9510'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Sustituye el indice unico de 'email' por una restriccion compuesta
    (email, eliminado_en) que permite reutilizar emails de cuentas eliminadas.
    """
    with op.batch_alter_table('usuarios', recreate='always') as batch_op:
        batch_op.drop_index('ix_usuarios_email')
        batch_op.create_index('ix_usuarios_email', ['email'], unique=False)
        batch_op.create_unique_constraint(
            'uq_usuarios_email_eliminado_en', ['email', 'eliminado_en']
        )


def downgrade() -> None:
    """Revierte al indice unico simple de email."""
    with op.batch_alter_table('usuarios', recreate='always') as batch_op:
        batch_op.drop_constraint('uq_usuarios_email_eliminado_en', type_='unique')
        batch_op.drop_index('ix_usuarios_email')
        batch_op.create_index('ix_usuarios_email', ['email'], unique=True)
