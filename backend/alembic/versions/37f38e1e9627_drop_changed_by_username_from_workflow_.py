"""drop_changed_by_username_from_workflow_ledger

Revision ID: 37f38e1e9627
Revises: 21ba337c441a
Create Date: 2026-06-29 16:42:45.496966

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '37f38e1e9627'
down_revision: Union[str, None] = '21ba337c441a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column('core_workflow_ledger', 'changed_by_username')


def downgrade() -> None:
    op.add_column('core_workflow_ledger', sa.Column('changed_by_username', sa.String(100), nullable=True))
