"""merge heads before last_date_property migration

Revision ID: 710be8def1f3
Revises: remove_system_col
Create Date: 2026-06-03 14:15:54.287649

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '710be8def1f3'
down_revision: Union[str, None] = 'remove_system_col'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
