"""add vendor to purchase_request

Revision ID: 47a0f88a119d
Revises: 6b75bbaa6385
Create Date: 2026-07-06 19:13:35.079753

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '47a0f88a119d'
down_revision: Union[str, None] = '6b75bbaa6385'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('purchase_request', sa.Column('vendor', sa.String(length=50), nullable=True))
    op.create_foreign_key('fk_purchase_request_vendor', 'purchase_request', 'vendor', ['vendor'], ['id'])


def downgrade() -> None:
    op.drop_constraint('fk_purchase_request_vendor', 'purchase_request', type_='foreignkey')
    op.drop_column('purchase_request', 'vendor')
