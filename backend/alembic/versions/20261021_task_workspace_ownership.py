"""Add explicit workspace ownership and integrity constraints to tasks.

Revision ID: 20261021_task_workspace
Revises: 20261021_workspace_schema
"""
from typing import Sequence, Union
import warnings

from alembic import op
import sqlalchemy as sa


revision: str = "20261021_task_workspace"
down_revision: Union[str, None] = "20261021_workspace_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("task")}
    if "workspace_id" not in columns:
        op.add_column("task", sa.Column("workspace_id", sa.String(50), nullable=True))

    bind.execute(
        sa.text(
            """
            UPDATE task
            SET workspace_id = (
                SELECT project.workspace_id
                FROM project
                WHERE project.id = task.project_id
            )
            WHERE workspace_id IS NULL
              AND EXISTS (
                  SELECT 1
                  FROM project
                  LEFT JOIN task_type ON task_type.id = task.task_type_id
                  WHERE project.id = task.project_id
                    AND project.workspace_id IS NOT NULL
                    AND (
                        task.task_type_id IS NULL
                        OR task_type.workspace_id = project.workspace_id
                    )
              )
            """
        )
    )
    unresolved_tasks = bind.scalar(
        sa.text(
            """
            SELECT count(*)
            FROM task
            LEFT JOIN project ON project.id = task.project_id
            LEFT JOIN task_type ON task_type.id = task.task_type_id
            WHERE task.workspace_id IS NULL
               OR task.workspace_id != project.workspace_id
               OR (
                   task.task_type_id IS NOT NULL
                   AND (
                       task_type.workspace_id IS NULL
                       OR task_type.workspace_id != project.workspace_id
                   )
               )
            """
        )
    )
    if unresolved_tasks:
        warnings.warn(
            f"{unresolved_tasks} tasks could not be mapped from their project and "
            "task type. They remain admin-only; resolve them through the "
            "workspace legacy-mapping API before granting operational access.",
            RuntimeWarning,
        )

    def has_unique(table: str, name: str) -> bool:
        inspector = sa.inspect(bind)
        return any(
            constraint.get("name") == name
            for constraint in inspector.get_unique_constraints(table)
        )

    if not has_unique("project", "uq_project_id_workspace"):
        with op.batch_alter_table("project") as batch:
            batch.create_unique_constraint(
                "uq_project_id_workspace", ["id", "workspace_id"]
            )
    if not has_unique("task_type", "uq_task_type_id_workspace"):
        with op.batch_alter_table("task_type") as batch:
            batch.create_unique_constraint(
                "uq_task_type_id_workspace", ["id", "workspace_id"]
            )

    inspector = sa.inspect(bind)
    foreign_keys = {
        foreign_key.get("name")
        for foreign_key in inspector.get_foreign_keys("task")
    }
    with op.batch_alter_table("task") as batch:
        batch.create_check_constraint(
            "ck_task_workspace_requires_project",
            "workspace_id IS NULL OR project_id IS NOT NULL",
        )
        if "fk_task_workspace" not in foreign_keys:
            batch.create_foreign_key(
                "fk_task_workspace", "workspace", ["workspace_id"], ["id"]
            )
        if "fk_task_project_workspace" not in foreign_keys:
            batch.create_foreign_key(
                "fk_task_project_workspace",
                "project",
                ["project_id", "workspace_id"],
                ["id", "workspace_id"],
            )
        if "fk_task_task_type_workspace" not in foreign_keys:
            batch.create_foreign_key(
                "fk_task_task_type_workspace",
                "task_type",
                ["task_type_id", "workspace_id"],
                ["id", "workspace_id"],
            )
    if not any(
        index["name"] == "ix_task_workspace_id"
        for index in sa.inspect(bind).get_indexes("task")
    ):
        op.create_index("ix_task_workspace_id", "task", ["workspace_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    foreign_keys = {
        foreign_key.get("name")
        for foreign_key in inspector.get_foreign_keys("task")
    }
    with op.batch_alter_table("task") as batch:
        batch.drop_constraint(
            "ck_task_workspace_requires_project", type_="check"
        )
        for name in (
            "fk_task_task_type_workspace",
            "fk_task_project_workspace",
            "fk_task_workspace",
        ):
            if name in foreign_keys:
                batch.drop_constraint(name, type_="foreignkey")

    if any(
        index["name"] == "ix_task_workspace_id"
        for index in sa.inspect(bind).get_indexes("task")
    ):
        op.drop_index("ix_task_workspace_id", table_name="task")

    if "workspace_id" in {
        column["name"] for column in sa.inspect(bind).get_columns("task")
    }:
        with op.batch_alter_table("task") as batch:
            batch.drop_column("workspace_id")

    for table, name in (
        ("task_type", "uq_task_type_id_workspace"),
        ("project", "uq_project_id_workspace"),
    ):
        if any(
            constraint.get("name") == name
            for constraint in sa.inspect(bind).get_unique_constraints(table)
        ):
            with op.batch_alter_table(table) as batch:
                batch.drop_constraint(name, type_="unique")
