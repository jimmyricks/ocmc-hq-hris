"""task deliverables: submission mode and submission content

Revision ID: 20261105_task_deliverables
Revises: 20261103_ws_task_workflows
Create Date: 2026-11-05 10:00:00.000000

"""
from datetime import datetime

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
import uuid

# revision identifiers, used by Alembic.
revision = '20261105_task_deliverables'
down_revision = '20261103_ws_task_workflows'
branch_labels = None
depends_on = None


def _table_names() -> set:
    return set(inspect(op.get_bind()).get_table_names())


def _column_names(table: str) -> set:
    return {c["name"] for c in inspect(op.get_bind()).get_columns(table)}


def _backfill_task_links() -> None:
    """Create a current task_link for tasks whose submissions carry a link
    but that have no task_link rows yet. Uses the newest submission link."""
    names = _table_names()
    if not {"task", "task_assignment", "task_submission", "task_link"} <= names:
        return

    bind = op.get_bind()
    rows = bind.execute(sa.text(
        """
        SELECT ta.task_id AS task_id, s.external_link AS external_link
        FROM task_submission s
        JOIN task_assignment ta ON ta.id = s.task_assignment_id
        WHERE s.external_link IS NOT NULL AND s.external_link != ''
        ORDER BY s.submitted_at IS NULL, s.submitted_at DESC, s.id DESC
        """
    )).fetchall()

    # Newest submission link wins per task.
    latest: dict = {}
    for task_id, external_link in rows:
        latest.setdefault(task_id, external_link)

    for task_id, url in latest.items():
        existing = bind.execute(sa.text(
            "SELECT COUNT(*) FROM task_link WHERE task_id = :task_id"
        ), {"task_id": task_id}).scalar()
        if existing:
            continue
        now = datetime.utcnow()
        bind.execute(
            sa.text(
                """
                INSERT INTO task_link (id, task_id, url, label, created_by, created_at, last_modified_by, updated_at)
                VALUES (:id, :task_id, :url, :label, NULL, :now, NULL, :now)
                """
            ),
            {
                "id": f"TLNK-MIG-{uuid.uuid4().hex[:10].upper()}",
                "task_id": task_id,
                "url": url,
                "label": "Submitted deliverable",
                "now": now,
            },
        )


def upgrade() -> None:
    names = _table_names()
    if "task_type" in names and "submission_mode" not in _column_names("task_type"):
        op.add_column(
            "task_type",
            sa.Column(
                "submission_mode",
                sa.String(length=20),
                nullable=True,
                server_default="link",
            ),
        )
    if "task_submission" in names and "content" not in _column_names("task_submission"):
        op.add_column("task_submission", sa.Column("content", sa.Text(), nullable=True))

    _backfill_task_links()


def downgrade() -> None:
    names = _table_names()
    if "task_submission" in names and "content" in _column_names("task_submission"):
        op.drop_column("task_submission", "content")
    if "task_type" in names and "submission_mode" in _column_names("task_type"):
        op.drop_column("task_type", "submission_mode")
