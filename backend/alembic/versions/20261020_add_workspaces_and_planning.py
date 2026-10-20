"""Add workspace and planning domain tables.

Revision ID: 20261020_workspaces
Revises: 66a03f8114a8
Create Date: 2026-10-20
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261020_workspaces"
down_revision: Union[str, None] = "66a03f8114a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _audit_columns():
    return [
        sa.Column("id", sa.String(length=50), nullable=False),
        sa.Column("created_by", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("last_modified_by", sa.String(length=50), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "workspace",
        *_audit_columns(),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("slug", sa.String(length=255), nullable=True),
        sa.Column("color", sa.String(length=255), nullable=True),
        sa.Column("timezone", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "workspace_membership",
        *_audit_columns(),
        sa.Column("workspace_id", sa.String(length=50), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("membership_role", sa.String(length=30), nullable=False),
        sa.Column("is_home", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("joined_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspace.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["core_users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "workspace_id", "user_id", name="uq_workspace_membership_user"
        ),
    )
    op.create_index(
        "ix_workspace_membership_workspace_id",
        "workspace_membership",
        ["workspace_id"],
    )
    op.create_index(
        "ix_workspace_membership_user_id", "workspace_membership", ["user_id"]
    )
    op.create_index(
        "uq_workspace_membership_home_user",
        "workspace_membership",
        ["user_id"],
        unique=True,
        sqlite_where=sa.text("is_home = 1"),
        postgresql_where=sa.text("is_home"),
    )
    op.create_table(
        "workspace_team",
        *_audit_columns(),
        sa.Column("workspace_id", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("head_user_id", sa.String(length=36), nullable=True),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspace.id"]),
        sa.ForeignKeyConstraint(["head_user_id"], ["core_users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workspace_id", "slug", name="uq_workspace_team_slug"),
    )
    op.create_index("ix_workspace_team_workspace_id", "workspace_team", ["workspace_id"])
    op.create_table(
        "workspace_resource",
        *_audit_columns(),
        sa.Column("workspace_id", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("resource_type", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspace.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_workspace_resource_workspace_id", "workspace_resource", ["workspace_id"]
    )
    op.create_table(
        "planner_event",
        *_audit_columns(),
        sa.Column("workspace_id", sa.String(length=50), nullable=False),
        sa.Column("team_id", sa.String(length=50), nullable=True),
        sa.Column("project_id", sa.String(length=50), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("starts_at", sa.DateTime(), nullable=False),
        sa.Column("ends_at", sa.DateTime(), nullable=False),
        sa.Column("timezone", sa.String(length=100), nullable=False),
        sa.Column("all_day", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspace.id"]),
        sa.ForeignKeyConstraint(["team_id"], ["workspace_team.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["project.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_planner_event_workspace_id", "planner_event", ["workspace_id"])
    op.create_index("ix_planner_event_team_id", "planner_event", ["team_id"])
    op.create_index("ix_planner_event_project_id", "planner_event", ["project_id"])
    op.create_index("ix_planner_event_starts_at", "planner_event", ["starts_at"])
    op.create_index("ix_planner_event_ends_at", "planner_event", ["ends_at"])
    op.create_table(
        "schedule_series",
        *_audit_columns(),
        sa.Column("workspace_id", sa.String(length=50), nullable=False),
        sa.Column("team_id", sa.String(length=50), nullable=True),
        sa.Column("project_id", sa.String(length=50), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("frequency", sa.String(length=20), nullable=False),
        sa.Column("interval", sa.Integer(), nullable=False),
        sa.Column("weekdays", sa.String(length=20), nullable=True),
        sa.Column("starts_at", sa.DateTime(), nullable=False),
        sa.Column("ends_at", sa.DateTime(), nullable=False),
        sa.Column("until_date", sa.Date(), nullable=False),
        sa.Column("timezone", sa.String(length=100), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspace.id"]),
        sa.ForeignKeyConstraint(["team_id"], ["workspace_team.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["project.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_schedule_series_workspace_id", "schedule_series", ["workspace_id"]
    )
    op.create_index("ix_schedule_series_team_id", "schedule_series", ["team_id"])
    op.create_index("ix_schedule_series_project_id", "schedule_series", ["project_id"])
    op.create_table(
        "schedule_occurrence",
        *_audit_columns(),
        sa.Column("series_id", sa.String(length=50), nullable=False),
        sa.Column("starts_at", sa.DateTime(), nullable=False),
        sa.Column("ends_at", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("title_override", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(["series_id"], ["schedule_series.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("series_id", "starts_at", name="uq_schedule_occurrence_start"),
    )
    op.create_index(
        "ix_schedule_occurrence_series_id", "schedule_occurrence", ["series_id"]
    )
    op.create_table(
        "resource_booking",
        *_audit_columns(),
        sa.Column("workspace_id", sa.String(length=50), nullable=False),
        sa.Column("resource_id", sa.String(length=50), nullable=False),
        sa.Column("event_id", sa.String(length=50), nullable=True),
        sa.Column("occurrence_id", sa.String(length=50), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("starts_at", sa.DateTime(), nullable=False),
        sa.Column("ends_at", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspace.id"]),
        sa.ForeignKeyConstraint(["resource_id"], ["workspace_resource.id"]),
        sa.ForeignKeyConstraint(["event_id"], ["planner_event.id"]),
        sa.ForeignKeyConstraint(["occurrence_id"], ["schedule_occurrence.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "resource_id",
            "starts_at",
            "ends_at",
            name="uq_resource_booking_interval",
        ),
    )
    op.create_index(
        "ix_resource_booking_workspace_id", "resource_booking", ["workspace_id"]
    )
    op.create_index(
        "ix_resource_booking_resource_id", "resource_booking", ["resource_id"]
    )
    op.create_index(
        "ix_resource_booking_starts_at", "resource_booking", ["starts_at"]
    )
    op.create_index("ix_resource_booking_ends_at", "resource_booking", ["ends_at"])

    with op.batch_alter_table("project") as batch_op:
        batch_op.add_column(sa.Column("workspace_id", sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column("team_id", sa.String(length=50), nullable=True))
        batch_op.create_foreign_key(
            "fk_project_workspace_id_workspace", "workspace", ["workspace_id"], ["id"]
        )
        batch_op.create_foreign_key(
            "fk_project_team_id_workspace_team",
            "workspace_team",
            ["team_id"],
            ["id"],
        )
        batch_op.create_index("ix_project_workspace_id", ["workspace_id"])
        batch_op.create_index("ix_project_team_id", ["team_id"])
    with op.batch_alter_table("task_type") as batch_op:
        batch_op.add_column(sa.Column("workspace_id", sa.String(length=50), nullable=True))
        batch_op.create_foreign_key(
            "fk_task_type_workspace_id_workspace", "workspace", ["workspace_id"], ["id"]
        )
        batch_op.create_index("ix_task_type_workspace_id", ["workspace_id"])
    op.add_column("task", sa.Column("planned_start_at", sa.DateTime(), nullable=True))
    op.add_column("task", sa.Column("planned_end_at", sa.DateTime(), nullable=True))
    with op.batch_alter_table("payroll_line_item") as batch_op:
        batch_op.add_column(
            sa.Column("workspace_id", sa.String(length=50), nullable=True)
        )
        batch_op.create_foreign_key(
            "fk_payroll_line_item_workspace_id_workspace",
            "workspace",
            ["workspace_id"],
            ["id"],
        )
        batch_op.create_index("ix_payroll_line_item_workspace_id", ["workspace_id"])


def downgrade() -> None:
    with op.batch_alter_table("payroll_line_item") as batch_op:
        batch_op.drop_index("ix_payroll_line_item_workspace_id")
        batch_op.drop_constraint(
            "fk_payroll_line_item_workspace_id_workspace", type_="foreignkey"
        )
        batch_op.drop_column("workspace_id")
    op.drop_column("task", "planned_end_at")
    op.drop_column("task", "planned_start_at")
    with op.batch_alter_table("task_type") as batch_op:
        batch_op.drop_index("ix_task_type_workspace_id")
        batch_op.drop_constraint(
            "fk_task_type_workspace_id_workspace", type_="foreignkey"
        )
        batch_op.drop_column("workspace_id")
    with op.batch_alter_table("project") as batch_op:
        batch_op.drop_index("ix_project_team_id")
        batch_op.drop_constraint(
            "fk_project_team_id_workspace_team", type_="foreignkey"
        )
        batch_op.drop_index("ix_project_workspace_id")
        batch_op.drop_constraint(
            "fk_project_workspace_id_workspace", type_="foreignkey"
        )
        batch_op.drop_column("workspace_id")
        batch_op.drop_column("team_id")
    for table, index in (
        ("resource_booking", "ix_resource_booking_ends_at"),
        ("resource_booking", "ix_resource_booking_starts_at"),
        ("resource_booking", "ix_resource_booking_resource_id"),
        ("resource_booking", "ix_resource_booking_workspace_id"),
        ("schedule_occurrence", "ix_schedule_occurrence_series_id"),
        ("schedule_series", "ix_schedule_series_project_id"),
        ("schedule_series", "ix_schedule_series_team_id"),
        ("schedule_series", "ix_schedule_series_workspace_id"),
        ("planner_event", "ix_planner_event_ends_at"),
        ("planner_event", "ix_planner_event_starts_at"),
        ("planner_event", "ix_planner_event_project_id"),
        ("planner_event", "ix_planner_event_team_id"),
        ("planner_event", "ix_planner_event_workspace_id"),
        ("workspace_resource", "ix_workspace_resource_workspace_id"),
        ("workspace_team", "ix_workspace_team_workspace_id"),
        ("workspace_membership", "uq_workspace_membership_home_user"),
        ("workspace_membership", "ix_workspace_membership_user_id"),
        ("workspace_membership", "ix_workspace_membership_workspace_id"),
    ):
        op.drop_index(index, table_name=table)
    for table in (
        "resource_booking",
        "schedule_occurrence",
        "schedule_series",
        "planner_event",
        "workspace_resource",
        "workspace_team",
        "workspace_membership",
        "workspace",
    ):
        op.drop_table(table)
