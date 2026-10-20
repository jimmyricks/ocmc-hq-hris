"""add_asset_class_to_maintenance_request

Revision ID: ec0e8a0fb560
Revises: 7119be878175
Create Date: 2026-06-04 11:42:22.700850

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ec0e8a0fb560'
down_revision: Union[str, None] = '7119be878175'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('maintenance_request', sa.Column('asset_class', sa.String(length=50), nullable=True))
    op.create_foreign_key(None, 'maintenance_request', 'asset_class', ['asset_class'], ['id'])


def downgrade() -> None:
    op.drop_constraint(None, 'maintenance_request', type_='foreignkey')
    op.drop_column('maintenance_request', 'asset_class')
