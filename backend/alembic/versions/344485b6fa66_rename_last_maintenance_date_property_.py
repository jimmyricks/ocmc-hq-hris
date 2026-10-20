"""rename_last_maintenance_date_property_to_last_date_property

Revision ID: 344485b6fa66
Revises: 710be8def1f3
Create Date: 2026-06-03 14:16:11.105525

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '344485b6fa66'
down_revision: Union[str, None] = '710be8def1f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Rename last_maintenance_date_property to last_date_property in maintenance_calendar table
    op.alter_column('maintenance_calendar', 'last_maintenance_date_property', new_column_name='last_date_property')


def downgrade() -> None:
    # Revert the rename
    op.alter_column('maintenance_calendar', 'last_date_property', new_column_name='last_maintenance_date_property')
