"""add_workflow_ledger

Revision ID: 03ceae4645ca
Revises: 20260623_user_settings_cols
Create Date: 2026-06-29 16:08:49.366649

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '03ceae4645ca'
down_revision: Union[str, None] = '20260623_user_settings_cols'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'core_workflow_ledger',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('entity_type', sa.String(100), nullable=False),
        sa.Column('record_id', sa.String(50), nullable=False),
        sa.Column('previous_state', sa.String(255), nullable=True),
        sa.Column('next_state', sa.String(255), nullable=False),
        sa.Column('action', sa.String(255), nullable=True),
        sa.Column('changed_by', sa.String(36), nullable=True),
        sa.Column('changed_by_username', sa.String(100), nullable=True),
        sa.Column('changed_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('triggered_by_entity_type', sa.String(100), nullable=True),
        sa.Column('triggered_by_record_id', sa.String(50), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Index('ix_core_workflow_ledger_entity_type', 'entity_type'),
        sa.Index('ix_core_workflow_ledger_record_id', 'record_id'),
        sa.Index('ix_core_workflow_ledger_changed_by', 'changed_by'),
    )


def downgrade() -> None:
    op.drop_table('core_workflow_ledger')
