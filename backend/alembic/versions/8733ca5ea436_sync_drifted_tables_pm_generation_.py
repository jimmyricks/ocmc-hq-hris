"""sync drifted tables pm_generation_ledger user_settings maintenance_plan

Revision ID: 8733ca5ea436
Revises: 47a0f88a119d
Create Date: 2026-07-06 19:16:46.177990

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '8733ca5ea436'
down_revision: Union[str, None] = '47a0f88a119d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── maintenance_plan: is_active nullable ──
    op.alter_column('maintenance_plan', 'is_active',
               existing_type=sa.BOOLEAN(),
               nullable=True,
               existing_server_default=sa.text('true'))

    # ── pm_generation_ledger: sync model drift ──
    op.add_column('pm_generation_ledger', sa.Column('created_at', sa.DateTime(), nullable=True))
    op.add_column('pm_generation_ledger', sa.Column('updated_at', sa.DateTime(), nullable=True))
    op.add_column('pm_generation_ledger', sa.Column('created_by', sa.String(length=36), nullable=True))
    op.add_column('pm_generation_ledger', sa.Column('last_modified_by', sa.String(length=36), nullable=True))
    op.alter_column('pm_generation_ledger', 'occurrence_key',
               existing_type=sa.VARCHAR(length=255),
               nullable=True)
    op.alter_column('pm_generation_ledger', 'schedule_type',
               existing_type=sa.VARCHAR(length=50),
               type_=sa.String(length=255),
               nullable=True)
    op.alter_column('pm_generation_ledger', 'generated_at',
               existing_type=postgresql.TIMESTAMP(),
               nullable=True)
    op.alter_column('pm_generation_ledger', 'job_run_id',
               existing_type=sa.VARCHAR(length=36),
               type_=sa.String(length=255),
               existing_nullable=True)
    op.alter_column('pm_generation_ledger', 'id',
               existing_type=sa.VARCHAR(length=36),
               type_=sa.String(length=50),
               existing_nullable=False)
    op.create_foreign_key('fk_pm_gen_ledger_maint_request', 'pm_generation_ledger', 'maintenance_request', ['maintenance_request'], ['id'])
    op.create_foreign_key('fk_pm_gen_ledger_wo_activity', 'pm_generation_ledger', 'work_order_activity', ['work_order_activity'], ['id'])
    op.create_foreign_key('fk_pm_gen_ledger_pma', 'pm_generation_ledger', 'planned_maintenance_activity', ['planned_maintenance_activity'], ['id'])
    op.create_foreign_key('fk_pm_gen_ledger_asset', 'pm_generation_ledger', 'asset', ['asset'], ['id'])
    op.drop_column('pm_generation_ledger', 'work_order')

    # ── user_settings: sync model drift ──
    op.alter_column('user_settings', 'id',
               existing_type=sa.VARCHAR(length=36),
               type_=sa.String(length=50),
               existing_nullable=False)
    op.alter_column('user_settings', 'created_at',
               existing_type=postgresql.TIMESTAMP(),
               nullable=False)
    op.alter_column('user_settings', 'updated_at',
               existing_type=postgresql.TIMESTAMP(),
               nullable=False)
    op.drop_constraint('user_settings_user_id_key', 'user_settings', type_='unique')
    op.drop_index('ix_user_settings_user_id', table_name='user_settings')
    op.create_index(op.f('ix_user_settings_user_id'), 'user_settings', ['user_id'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_user_settings_user_id'), table_name='user_settings')
    op.create_index('ix_user_settings_user_id', 'user_settings', ['user_id'], unique=False)
    op.create_unique_constraint('user_settings_user_id_key', 'user_settings', ['user_id'])
    op.alter_column('user_settings', 'updated_at',
               existing_type=postgresql.TIMESTAMP(),
               nullable=True)
    op.alter_column('user_settings', 'created_at',
               existing_type=postgresql.TIMESTAMP(),
               nullable=True)
    op.alter_column('user_settings', 'id',
               existing_type=sa.String(length=50),
               type_=sa.VARCHAR(length=36),
               existing_nullable=False)
    op.add_column('pm_generation_ledger', sa.Column('work_order', sa.VARCHAR(length=50), autoincrement=False, nullable=True))
    op.drop_constraint('fk_pm_gen_ledger_asset', 'pm_generation_ledger', type_='foreignkey')
    op.drop_constraint('fk_pm_gen_ledger_pma', 'pm_generation_ledger', type_='foreignkey')
    op.drop_constraint('fk_pm_gen_ledger_wo_activity', 'pm_generation_ledger', type_='foreignkey')
    op.drop_constraint('fk_pm_gen_ledger_maint_request', 'pm_generation_ledger', type_='foreignkey')
    op.alter_column('pm_generation_ledger', 'id',
               existing_type=sa.String(length=50),
               type_=sa.VARCHAR(length=36),
               existing_nullable=False)
    op.alter_column('pm_generation_ledger', 'job_run_id',
               existing_type=sa.String(length=255),
               type_=sa.VARCHAR(length=36),
               existing_nullable=True)
    op.alter_column('pm_generation_ledger', 'generated_at',
               existing_type=postgresql.TIMESTAMP(),
               nullable=False)
    op.alter_column('pm_generation_ledger', 'schedule_type',
               existing_type=sa.String(length=255),
               type_=sa.VARCHAR(length=50),
               nullable=False)
    op.alter_column('pm_generation_ledger', 'occurrence_key',
               existing_type=sa.VARCHAR(length=255),
               nullable=False)
    op.drop_column('pm_generation_ledger', 'last_modified_by')
    op.drop_column('pm_generation_ledger', 'created_by')
    op.drop_column('pm_generation_ledger', 'updated_at')
    op.drop_column('pm_generation_ledger', 'created_at')
    op.alter_column('maintenance_plan', 'is_active',
               existing_type=sa.BOOLEAN(),
               nullable=False,
               existing_server_default=sa.text('true'))
