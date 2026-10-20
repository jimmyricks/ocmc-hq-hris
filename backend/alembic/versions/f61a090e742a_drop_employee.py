"""drop_employee

Revision ID: f61a090e742a
Revises: c2eae0f83820
Create Date: 2026-07-15 06:09:36.244513

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f61a090e742a'
down_revision: Union[str, None] = 'c2eae0f83820'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop the deprecated employee table now that the User entity is the single identity."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if inspector.has_table('employee'):
        op.drop_table('employee')


def downgrade() -> None:
    """Recreate the employee table for rollback scenarios."""
    op.create_table(
        'employee',
        sa.Column('id', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('user_id', sa.String(length=50), nullable=True),
        sa.Column('employee_code', sa.String(length=255), nullable=True),
        sa.Column('department_id', sa.String(length=50), nullable=True),
        sa.Column('position', sa.String(length=255), nullable=True),
        sa.Column('employment_type', sa.String(length=100), nullable=True),
        sa.Column('date_joined', sa.Date(), nullable=True),
        sa.Column('date_resigned', sa.Date(), nullable=True),
        sa.Column('bank_name', sa.String(length=255), nullable=True),
        sa.Column('bank_account_no', sa.String(length=255), nullable=True),
        sa.Column('tax_id', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=100), nullable=True),
        sa.Column('created_by', sa.String(length=50), nullable=True),
        sa.Column('last_modified_by', sa.String(length=50), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['core_users.id']),
        sa.ForeignKeyConstraint(['department_id'], ['department.id']),
        sa.ForeignKeyConstraint(['created_by'], ['core_users.id']),
        sa.ForeignKeyConstraint(['last_modified_by'], ['core_users.id']),
    )
