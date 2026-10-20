"""Align workspace column constraints with the ORM domain models.

Revision ID: 20261021_workspace_schema
Revises: 1aaef8fe765b
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261021_workspace_schema"
down_revision: Union[str, None] = "1aaef8fe765b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_index(bind, table: str, name: str) -> bool:
    return any(
        index["name"] == name for index in sa.inspect(bind).get_indexes(table)
    )


def _has_unique(bind, table: str, columns: list[str]) -> bool:
    return any(
        constraint.get("column_names") == columns
        for constraint in sa.inspect(bind).get_unique_constraints(table)
    )


def _has_constraint(bind, table: str, name: str) -> bool:
    return any(
        constraint.get("name") == name
        for constraint in sa.inspect(bind).get_unique_constraints(table)
    )


def upgrade() -> None:
    bind = op.get_bind()
    invalid_workspace_data = bind.scalar(
        sa.text(
            """
            SELECT count(*)
            FROM workspace
            WHERE name IS NULL
               OR slug IS NULL
               OR length(slug) > 100
               OR color IS NULL
               OR length(color) > 7
               OR timezone IS NULL
               OR length(timezone) > 100
               OR is_active IS NULL
            """
        )
    )
    if invalid_workspace_data:
        raise RuntimeError(
            "Workspace rows must be mapped to valid names, unique slugs, colors, "
            "timezones, and active states before this migration."
        )

    invalid_event_data = bind.scalar(
        sa.text("SELECT count(*) FROM planner_event WHERE workspace_id IS NULL")
    )
    if invalid_event_data:
        raise RuntimeError(
            "Planner events without workspace ownership must be mapped before migration."
        )

    invalid_team_data = bind.scalar(
        sa.text(
            """
            SELECT count(*)
            FROM workspace_team
            WHERE workspace_id IS NULL OR name IS NULL OR slug IS NULL
               OR length(slug) > 100
            """
        )
    )
    duplicate_workspace_slugs = bind.scalar(
        sa.text(
            """
            SELECT count(*)
            FROM (SELECT slug FROM workspace GROUP BY slug HAVING count(*) > 1) d
            """
        )
    )
    duplicate_team_slugs = bind.scalar(
        sa.text(
            """
            SELECT count(*)
            FROM (
                SELECT workspace_id, slug
                FROM workspace_team
                GROUP BY workspace_id, slug
                HAVING count(*) > 1
            ) d
            """
        )
    )
    if invalid_team_data or duplicate_workspace_slugs or duplicate_team_slugs:
        raise RuntimeError(
            "Workspace and team ownership values must be valid and unique before "
            "the workspace schema can be tightened."
        )

    with op.batch_alter_table("workspace") as batch:
        batch.alter_column("name", existing_type=sa.String(255), nullable=False)
        batch.alter_column(
            "slug",
            existing_type=sa.String(255),
            type_=sa.String(100),
            nullable=False,
        )
        batch.alter_column(
            "color",
            existing_type=sa.String(255),
            type_=sa.String(7),
            nullable=False,
        )
        batch.alter_column(
            "timezone",
            existing_type=sa.String(255),
            type_=sa.String(100),
            nullable=False,
        )
        batch.alter_column(
            "is_active", existing_type=sa.Boolean(), nullable=False
        )
        if not _has_unique(bind, "workspace", ["slug"]):
            batch.create_unique_constraint("uq_workspace_slug", ["slug"])

    with op.batch_alter_table("planner_event") as batch:
        batch.alter_column(
            "workspace_id",
            existing_type=sa.String(50),
            nullable=False,
        )

    with op.batch_alter_table("workspace_team") as batch:
        batch.alter_column(
            "workspace_id",
            existing_type=sa.String(50),
            nullable=False,
        )
        batch.alter_column("name", existing_type=sa.String(255), nullable=False)
        batch.alter_column(
            "slug",
            existing_type=sa.String(255),
            type_=sa.String(100),
            nullable=False,
        )
        if not _has_unique(bind, "workspace_team", ["workspace_id", "slug"]):
            batch.create_unique_constraint(
                "uq_workspace_team_slug", ["workspace_id", "slug"]
            )

    for table, name, columns in (
        ("project", "ix_project_workspace_id", ["workspace_id"]),
        ("project", "ix_project_team_id", ["team_id"]),
        ("task_type", "ix_task_type_workspace_id", ["workspace_id"]),
        (
            "payroll_line_item",
            "ix_payroll_line_item_workspace_id",
            ["workspace_id"],
        ),
        ("workspace_team", "ix_workspace_team_workspace_id", ["workspace_id"]),
    ):
        if not _has_index(bind, table, name):
            op.create_index(name, table, columns)


def downgrade() -> None:
    bind = op.get_bind()
    if _has_constraint(bind, "workspace", "uq_workspace_slug"):
        with op.batch_alter_table("workspace") as batch:
            batch.drop_constraint("uq_workspace_slug", type_="unique")
    if _has_constraint(bind, "workspace_team", "uq_workspace_team_slug"):
        with op.batch_alter_table("workspace_team") as batch:
            batch.drop_constraint("uq_workspace_team_slug", type_="unique")

    for table, name in (
        ("workspace_team", "ix_workspace_team_workspace_id"),
        ("payroll_line_item", "ix_payroll_line_item_workspace_id"),
        ("task_type", "ix_task_type_workspace_id"),
        ("project", "ix_project_team_id"),
        ("project", "ix_project_workspace_id"),
    ):
        if _has_index(bind, table, name):
            op.drop_index(name, table_name=table)

    with op.batch_alter_table("planner_event") as batch:
        batch.alter_column(
            "workspace_id",
            existing_type=sa.String(50),
            nullable=True,
        )
    with op.batch_alter_table("workspace_team") as batch:
        batch.alter_column("slug", type_=sa.String(255), nullable=True)
        batch.alter_column("name", nullable=True)
        batch.alter_column("workspace_id", nullable=True)
    with op.batch_alter_table("workspace") as batch:
        batch.alter_column("is_active", nullable=True)
        batch.alter_column("timezone", type_=sa.String(255), nullable=True)
        batch.alter_column("color", type_=sa.String(255), nullable=True)
        batch.alter_column("slug", type_=sa.String(255), nullable=True)
        batch.alter_column("name", nullable=True)
