"""add visual_config to workflow transitions

Revision ID: a1b2c3d4e5f6
Revises: b556c9725ce8
Create Date: 2026-07-08 16:37:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'b556c9725ce8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add visual_config to both tables
    op.add_column('core_workflow_state_links', sa.Column('visual_config', sa.Text(), nullable=True))
    op.add_column('core_workflow_transitions', sa.Column('visual_config', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('core_workflow_transitions', 'visual_config')
    op.drop_column('core_workflow_state_links', 'visual_config')
