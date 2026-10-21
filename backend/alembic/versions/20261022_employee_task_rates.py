"""Add employee task rates and immutable approval pay snapshots.

Revision ID: 20261022_employee_task_rates
Revises: 20261021_task_workspace
"""
from typing import Sequence, Union
import warnings

from alembic import op
import sqlalchemy as sa


revision: str = "20261022_employee_task_rates"
down_revision: Union[str, None] = "20261021_task_workspace"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    approved_without_snapshot = bind.scalar(
        sa.text(
            """
            SELECT count(*)
            FROM task_submission
            WHERE status = 'approved'
            """
        )
    )
    if approved_without_snapshot:
        warnings.warn(
            f"{approved_without_snapshot} previously approved task submissions have "
            "no approved pay snapshot. Their historical pay is intentionally not "
            "inferred from today's rates; review and resolve these submissions "
            "before including them in payroll.",
            RuntimeWarning,
        )

    duplicate_invoice_entries = bind.scalar(
        sa.text(
            """
            SELECT count(*)
            FROM (
                SELECT payroll_entry_id
                FROM invoice
                WHERE payroll_entry_id IS NOT NULL
                GROUP BY payroll_entry_id
                HAVING count(*) > 1
            ) duplicates
            """
        )
    )
    if duplicate_invoice_entries:
        raise RuntimeError(
            "Duplicate invoices exist for a payroll entry. Reconcile them before "
            "adding the invoice idempotency constraint."
        )

    inspector = sa.inspect(bind)
    submission_columns = {
        column["name"] for column in inspector.get_columns("task_submission")
    }
    with op.batch_alter_table("task_submission") as batch:
        for column_name in ("approved_rate", "approved_quantity", "approved_amount"):
            if column_name not in submission_columns:
                batch.add_column(
                    sa.Column(column_name, sa.Numeric(12, 2), nullable=True)
                )

    if not inspector.has_table("user_task_rate"):
        op.create_table(
            "user_task_rate",
            sa.Column("id", sa.String(length=50), nullable=False),
            sa.Column("created_by", sa.String(length=50), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("last_modified_by", sa.String(length=50), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("workspace_id", sa.String(length=50), nullable=False),
            sa.Column("task_type_id", sa.String(length=50), nullable=False),
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.Column("rate", sa.Numeric(12, 2), nullable=False),
            sa.CheckConstraint("rate > 0", name="ck_user_task_rate_positive"),
            sa.ForeignKeyConstraint(["workspace_id"], ["workspace.id"]),
            sa.ForeignKeyConstraint(["task_type_id"], ["task_type.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["core_users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "workspace_id",
                "task_type_id",
                "user_id",
                name="uq_user_task_rate_workspace_type_user",
            ),
        )
    else:
        expected_columns = {
            "id",
            "created_by",
            "created_at",
            "last_modified_by",
            "updated_at",
            "workspace_id",
            "task_type_id",
            "user_id",
            "rate",
        }
        present_columns = {
            column["name"] for column in inspector.get_columns("user_task_rate")
        }
        missing_columns = expected_columns - present_columns
        if missing_columns:
            raise RuntimeError(
                "Existing user_task_rate table is incomplete; missing columns: "
                + ", ".join(sorted(missing_columns))
            )

    existing_indexes = {
        index["name"] for index in sa.inspect(bind).get_indexes("user_task_rate")
    }
    index_specs = (
        ("ix_user_task_rate_workspace_id", ["workspace_id"]),
        ("ix_user_task_rate_task_type_id", ["task_type_id"]),
        ("ix_user_task_rate_user_id", ["user_id"]),
        ("ix_user_task_rate_user_workspace", ["user_id", "workspace_id"]),
    )
    for index_name, columns in index_specs:
        if index_name not in existing_indexes:
            op.create_index(index_name, "user_task_rate", columns)

    invoice_uniques = {
        constraint.get("name")
        for constraint in sa.inspect(bind).get_unique_constraints("invoice")
    }
    if "uq_invoice_payroll_entry_id" not in invoice_uniques:
        with op.batch_alter_table("invoice") as batch:
            batch.create_unique_constraint(
                "uq_invoice_payroll_entry_id", ["payroll_entry_id"]
            )


def downgrade() -> None:
    with op.batch_alter_table("invoice") as batch:
        batch.drop_constraint("uq_invoice_payroll_entry_id", type_="unique")
    op.drop_index("ix_user_task_rate_user_workspace", table_name="user_task_rate")
    op.drop_index("ix_user_task_rate_user_id", table_name="user_task_rate")
    op.drop_index("ix_user_task_rate_task_type_id", table_name="user_task_rate")
    op.drop_index("ix_user_task_rate_workspace_id", table_name="user_task_rate")
    op.drop_table("user_task_rate")
    with op.batch_alter_table("task_submission") as batch:
        batch.drop_column("approved_amount")
        batch.drop_column("approved_quantity")
        batch.drop_column("approved_rate")
