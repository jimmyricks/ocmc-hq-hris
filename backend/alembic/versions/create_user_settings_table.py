"""create user_settings table

Revision ID: create_user_settings_table
Revises: ec0e8a0fb560
Create Date: 2026-06-22 19:00:00.000000

"""
from typing import Sequence, Union
from datetime import datetime

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'create_user_settings_table'
down_revision: Union[str, None] = 'ec0e8a0fb560'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'user_settings',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('dashboard_card_filter', sa.String(length=50), nullable=True),
        sa.Column('dashboard_card_type', sa.String(length=50), nullable=True),
        sa.Column('dashboard_field_config', postgresql.JSON(), nullable=True),
        sa.Column('dashboard_selections', postgresql.JSON(), nullable=True),
        sa.Column('theme', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime(), nullable=True, default=datetime.utcnow),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )
    op.create_index('ix_user_settings_user_id', 'user_settings', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_user_settings_user_id', table_name='user_settings')
    op.drop_table('user_settings')
