"""add_dashboard_selections_column

Revision ID: add_dashboard_selections_column
Revises: ec0e8a0fb560
Create Date: 2026-06-22 19:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'add_dashboard_selections_column'
down_revision: Union[str, None] = 'create_user_settings_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Column already created by create_user_settings_table migration
    pass


def downgrade() -> None:
    pass
