"""add_work_order_to_maintenance_request

Revision ID: 20353c40a251
Revises: ec0e8a0fb560
Create Date: 2026-06-04 11:53:17.236945

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20353c40a251'
down_revision: Union[str, None] = 'ec0e8a0fb560'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('maintenance_request', sa.Column('work_order', sa.String(length=50), nullable=True))
    op.create_foreign_key(None, 'maintenance_request', 'work_order', ['work_order'], ['id'])


def downgrade() -> None:
    op.drop_constraint(None, 'maintenance_request', type_='foreignkey')
    op.drop_column('maintenance_request', 'work_order')
