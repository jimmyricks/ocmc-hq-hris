"""merge workflow transition refactor with visual config migration

Revision ID: 90732c2995aa
Revises: a1b2c3d4e5f6, refactor_workflow_transitions_to_use_state_links
Create Date: 2026-07-09 00:50:01.526681

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '90732c2995aa'
down_revision: Union[str, None] = ('a1b2c3d4e5f6', 'refactor_transitions_links')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
