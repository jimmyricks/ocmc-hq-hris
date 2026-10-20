"""add bin.rack and inventory.rack FK columns

Revision ID: 6b75bbaa6385
Revises: 403b93b54932
Create Date: 2026-07-06 16:48:37.916252

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '6b75bbaa6385'
down_revision: Union[str, None] = '403b93b54932'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('bin', sa.Column('rack', sa.String(length=50), nullable=True))
    op.create_foreign_key('bin_rack_fkey', 'bin', 'rack', ['rack'], ['id'])
    op.add_column('inventory', sa.Column('rack', sa.String(length=50), nullable=True))
    op.create_foreign_key('inventory_rack_fkey', 'inventory', 'rack', ['rack'], ['id'])


def downgrade() -> None:
    op.drop_constraint('inventory_rack_fkey', 'inventory', type_='foreignkey')
    op.drop_column('inventory', 'rack')
    op.drop_constraint('bin_rack_fkey', 'bin', type_='foreignkey')
    op.drop_column('bin', 'rack')
