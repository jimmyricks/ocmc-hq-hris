"""add shelf.rack_name and bin.shelf_name denormalized fields

Revision ID: 403b93b54932
Revises: 4d8af8f57b33
Create Date: 2026-07-06 16:35:16.337231

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '403b93b54932'
down_revision: Union[str, None] = '4d8af8f57b33'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('bin', sa.Column('shelf_name', sa.String(length=255), nullable=True))
    op.add_column('shelf', sa.Column('rack_name', sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column('shelf', 'rack_name')
    op.drop_column('bin', 'shelf_name')
