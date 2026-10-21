"""Move planned task bounds to projects and support continuous projects.

Revision ID: 20261023_project_schedule
Revises: 20261022_employee_task_rates
"""
from datetime import date, datetime
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261023_project_schedule"
down_revision: Union[str, None] = "20261022_employee_task_rates"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _as_date(value) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    project_columns = {
        column["name"] for column in inspector.get_columns("project")
    }
    if "is_continuous" not in project_columns:
        op.add_column(
            "project",
            sa.Column(
                "is_continuous",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
        )

    task_columns = {
        column["name"] for column in sa.inspect(bind).get_columns("task")
    }
    planned_columns = {"planned_start_at", "planned_end_at"} & task_columns
    if planned_columns:
        task = sa.Table("task", sa.MetaData(), autoload_with=bind)
        project = sa.Table("project", sa.MetaData(), autoload_with=bind)
        aggregate_columns = [task.c.project_id]
        if "planned_start_at" in planned_columns:
            aggregate_columns.append(sa.func.min(task.c.planned_start_at))
        else:
            aggregate_columns.append(sa.null())
        if "planned_end_at" in planned_columns:
            aggregate_columns.append(sa.func.max(task.c.planned_end_at))
        else:
            aggregate_columns.append(sa.null())

        for project_id, raw_start, raw_end in bind.execute(
            sa.select(*aggregate_columns)
            .where(task.c.project_id.is_not(None))
            .group_by(task.c.project_id)
        ):
            start_date = _as_date(raw_start)
            end_date = _as_date(raw_end)
            existing = bind.execute(
                sa.select(project.c.start_date, project.c.end_date).where(
                    project.c.id == project_id
                )
            ).first()
            if not existing:
                continue
            updates = {}
            if existing.start_date is None and start_date is not None:
                updates["start_date"] = start_date
            if existing.end_date is None and end_date is not None:
                updates["end_date"] = end_date
            if updates:
                bind.execute(
                    sa.update(project)
                    .where(project.c.id == project_id)
                    .values(**updates)
                )

        with op.batch_alter_table("task") as batch:
            for column in ("planned_start_at", "planned_end_at"):
                if column in planned_columns:
                    batch.drop_column(column)


def downgrade() -> None:
    bind = op.get_bind()
    task_columns = {
        column["name"] for column in sa.inspect(bind).get_columns("task")
    }
    with op.batch_alter_table("task") as batch:
        if "planned_start_at" not in task_columns:
            batch.add_column(sa.Column("planned_start_at", sa.DateTime(), nullable=True))
        if "planned_end_at" not in task_columns:
            batch.add_column(sa.Column("planned_end_at", sa.DateTime(), nullable=True))

    if "is_continuous" in {
        column["name"] for column in sa.inspect(bind).get_columns("project")
    }:
        with op.batch_alter_table("project") as batch:
            batch.drop_column("is_continuous")
