"""drop bin rack_name shelf_name columns

Revision ID: 4d8af8f57b33
Revises: 9f5a3f9194b9
Create Date: 2026-07-06 16:01:25.514472

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '4d8af8f57b33'
down_revision: Union[str, None] = '9f5a3f9194b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column('bin', 'rack_name')
    op.drop_column('bin', 'shelf_name')


def downgrade() -> None:
    op.add_column('bin', sa.Column('shelf_name', sa.VARCHAR(length=255), autoincrement=False, nullable=True))
    op.add_column('bin', sa.Column('rack_name', sa.VARCHAR(length=255), autoincrement=False, nullable=True))
