"""Scope workflows to workspaces and support scoped defaults.

Revision ID: 20261103_ws_task_workflows
Revises: 20261023_project_schedule
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261103_ws_task_workflows"
down_revision: Union[str, None] = "20261023_project_schedule"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


WORKSPACE_INDEX = "ix_core_workflows_workspace_id"
SCOPE_INDEX = "ix_core_workflows_scope"
DEFAULT_INDEX = "uq_core_workflows_default_scope"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("core_workflows"):
        return

    columns = {column["name"] for column in inspector.get_columns("core_workflows")}
    with op.batch_alter_table("core_workflows") as batch:
        if "workspace_id" not in columns:
            batch.add_column(sa.Column("workspace_id", sa.String(length=50), nullable=True))
            batch.create_foreign_key(
                "fk_core_workflows_workspace_id",
                "workspace",
                ["workspace_id"],
                ["id"],
            )
        if "is_default" not in columns:
            batch.add_column(
                sa.Column(
                    "is_default",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.false(),
                )
            )

    indexes = {index["name"] for index in sa.inspect(bind).get_indexes("core_workflows")}
    if WORKSPACE_INDEX not in indexes:
        op.create_index(WORKSPACE_INDEX, "core_workflows", ["workspace_id"])
    if SCOPE_INDEX not in indexes:
        op.create_index(
            SCOPE_INDEX,
            "core_workflows",
            ["workspace_id", "target_entity"],
        )
    if DEFAULT_INDEX not in indexes:
        op.create_index(
            DEFAULT_INDEX,
            "core_workflows",
            ["workspace_id", "target_entity"],
            unique=True,
            sqlite_where=sa.text("is_default = 1"),
            postgresql_where=sa.text("is_default"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("core_workflows"):
        return

    indexes = {index["name"] for index in inspector.get_indexes("core_workflows")}
    for index_name in (DEFAULT_INDEX, SCOPE_INDEX, WORKSPACE_INDEX):
        if index_name in indexes:
            op.drop_index(index_name, table_name="core_workflows")

    columns = {column["name"] for column in inspector.get_columns("core_workflows")}
    with op.batch_alter_table("core_workflows") as batch:
        if "is_default" in columns:
            batch.drop_column("is_default")
        if "workspace_id" in columns:
            batch.drop_constraint(
                "fk_core_workflows_workspace_id", type_="foreignkey"
            )
            batch.drop_column("workspace_id")
