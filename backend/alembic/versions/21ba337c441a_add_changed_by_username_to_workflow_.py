"""add_changed_by_username_to_workflow_ledger

Revision ID: 21ba337c441a
Revises: 03ceae4645ca
Create Date: 2026-06-29 16:41:10.391069

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '21ba337c441a'
down_revision: Union[str, None] = '03ceae4645ca'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('core_workflow_ledger', sa.Column('changed_by_username', sa.String(100), nullable=True))


def downgrade() -> None:
    op.drop_column('core_workflow_ledger', 'changed_by_username')
