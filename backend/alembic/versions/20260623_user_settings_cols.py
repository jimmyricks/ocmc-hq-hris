"""add_created_by_last_modified_by_to_user_settings

Revision ID: 20260623_add_created_by_last_modified_by_to_user_settings
Revises: add_dashboard_selections_column
Create Date: 2026-06-23 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260623_user_settings_cols'
down_revision: Union[str, None] = 'add_dashboard_selections_column'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('user_settings', sa.Column('created_by', sa.String(length=36), nullable=True))
    op.add_column('user_settings', sa.Column('last_modified_by', sa.String(length=36), nullable=True))


def downgrade() -> None:
    op.drop_column('user_settings', 'last_modified_by')
    op.drop_column('user_settings', 'created_by')
