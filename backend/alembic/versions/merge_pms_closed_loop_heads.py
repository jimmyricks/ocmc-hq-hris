"""Merge heads for PMS closed-loop continuity

Revision ID: merge_pms_closed_loop_heads
Revises: 0059_add_pm_generation_ledger, 344485b6fa66
Create Date: 2026-06-03 15:59:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'merge_pms_closed_loop_heads'
down_revision: Union[str, None] = ('0059_add_pm_generation_ledger', '344485b6fa66')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
