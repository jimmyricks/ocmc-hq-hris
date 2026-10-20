"""drop_file_add_external_link

Revision ID: c2eae0f83820
Revises: 499eafc6ac5b
Create Date: 2026-07-15 05:54:05.191586

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c2eae0f83820'
down_revision: Union[str, None] = '499eafc6ac5b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Remove the File entity/table which is no longer part of the system.
    if "file" in inspector.get_table_names():
        op.drop_table("file")

    # Add a nullable link column to task submissions for external deliverables.
    columns = [c["name"] for c in inspector.get_columns("task_submission")]
    if "external_link" not in columns:
        op.add_column(
            "task_submission",
            sa.Column("external_link", sa.String(255), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    columns = [c["name"] for c in inspector.get_columns("task_submission")]
    if "external_link" in columns:
        op.drop_column("task_submission", "external_link")

    if "file" not in inspector.get_table_names():
        op.create_table(
            "file",
            sa.Column("id", sa.String(50), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.Column("reference_entity", sa.String(), nullable=False),
            sa.Column("reference_id", sa.String(), nullable=False),
            sa.Column("file_name", sa.String(), nullable=False),
            sa.Column("file_path", sa.String(), nullable=False),
            sa.Column("file_type", sa.String(), nullable=True),
            sa.Column("file_size", sa.Integer(), nullable=True),
            sa.Column("uploaded_by", sa.String(50), nullable=True),
            sa.Column("uploaded_at", sa.DateTime(), nullable=True),
            sa.Column("created_by", sa.String(50), nullable=True),
            sa.Column("last_modified_by", sa.String(50), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
