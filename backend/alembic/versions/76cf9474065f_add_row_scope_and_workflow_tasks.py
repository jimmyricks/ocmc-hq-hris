"""add row scope and workflow tasks

Revision ID: 76cf9474065f
Revises: 90732c2995aa
Create Date: 2026-07-10 00:03:15.621483

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '76cf9474065f'
down_revision: Union[str, None] = '90732c2995aa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'core_entity_permissions',
        sa.Column('row_scope', sa.String(20), nullable=False, server_default='all')
    )


def downgrade() -> None:
    op.drop_column('core_entity_permissions', 'row_scope')
