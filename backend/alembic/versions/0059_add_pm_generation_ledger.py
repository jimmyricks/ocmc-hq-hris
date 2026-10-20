"""Add pm_generation_ledger table for scheduler idempotency

Revision ID: 0059_add_pm_generation_ledger
Revises: b0e2d66f8106_merge_heads_before_notification_
Create Date: 2026-06-03 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0059_add_pm_generation_ledger'
down_revision = 'b0e2d66f8106'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'pm_generation_ledger',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('occurrence_key', sa.String(255), nullable=False),
        sa.Column('schedule_type', sa.String(50), nullable=False),
        sa.Column('asset', sa.String(50), nullable=True),
        sa.Column('planned_maintenance_activity', sa.String(50), nullable=True),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.Column('maintenance_request', sa.String(50), nullable=True),
        sa.Column('work_order_activity', sa.String(50), nullable=True),
        sa.Column('generated_at', sa.DateTime(), nullable=False,
                  server_default=sa.func.now()),
        sa.Column('job_run_id', sa.String(36), nullable=True),
        sa.UniqueConstraint('occurrence_key', name='uq_pm_generation_ledger_occurrence_key'),
    )


def downgrade() -> None:
    op.drop_table('pm_generation_ledger')
