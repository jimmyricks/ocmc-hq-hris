"""add rack shelf tables and bin.shelf FK

Revision ID: 9f5a3f9194b9
Revises: 4bc049c65507
Create Date: 2026-07-06 15:52:56.924751

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '9f5a3f9194b9'
down_revision: Union[str, None] = '4bc049c65507'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('rack',
    sa.Column('rack_name', sa.String(length=255), nullable=True),
    sa.Column('store', sa.String(length=50), nullable=True),
    sa.Column('store_name', sa.String(length=255), nullable=True),
    sa.Column('site', sa.String(length=50), nullable=True),
    sa.Column('id', sa.String(length=50), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.Column('created_by', sa.String(length=36), nullable=True),
    sa.Column('last_modified_by', sa.String(length=36), nullable=True),
    sa.ForeignKeyConstraint(['site'], ['site.id'], ),
    sa.ForeignKeyConstraint(['store'], ['store.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('shelf',
    sa.Column('shelf_name', sa.String(length=255), nullable=True),
    sa.Column('rack', sa.String(length=50), nullable=True),
    sa.Column('store', sa.String(length=50), nullable=True),
    sa.Column('store_name', sa.String(length=255), nullable=True),
    sa.Column('site', sa.String(length=50), nullable=True),
    sa.Column('id', sa.String(length=50), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.Column('created_by', sa.String(length=36), nullable=True),
    sa.Column('last_modified_by', sa.String(length=36), nullable=True),
    sa.ForeignKeyConstraint(['rack'], ['rack.id'], ),
    sa.ForeignKeyConstraint(['site'], ['site.id'], ),
    sa.ForeignKeyConstraint(['store'], ['store.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.add_column('bin', sa.Column('shelf', sa.String(length=50), nullable=True))
    op.create_foreign_key('bin_shelf_fkey', 'bin', 'shelf', ['shelf'], ['id'])


def downgrade() -> None:
    op.drop_constraint('bin_shelf_fkey', 'bin', type_='foreignkey')
    op.drop_column('bin', 'shelf')
    op.drop_table('shelf')
    op.drop_table('rack')
