"""Add scoped Bahandi project fields and integration delivery records."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261106_bahandi_integration"
down_revision: Union[str, None] = "20261105_task_deliverables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _columns(table: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(table):
        return set()
    return {column["name"] for column in inspector.get_columns(table)}


def _create_columns(table: str, columns: list[sa.Column]) -> None:
    existing = _columns(table)
    if not existing:
        return
    with op.batch_alter_table(table) as batch:
        for column in columns:
            if column.name not in existing:
                batch.add_column(column)


def upgrade() -> None:
    _create_columns(
        "project",
        [
            sa.Column("bahandi_artist_id", sa.Integer(), nullable=True),
            sa.Column("integration_kind", sa.String(length=30), nullable=True),
            sa.Column(
                "artist_portal_visible",
                sa.Boolean(),
                nullable=True,
                server_default=sa.false(),
            ),
            sa.Column("public_summary", sa.String(length=2000), nullable=True),
        ],
    )
    _create_columns(
        "task",
        [
            sa.Column("artist_portal_kind", sa.String(length=30), nullable=True),
            sa.Column("public_summary", sa.String(length=2000), nullable=True),
            sa.Column("integration_kind", sa.String(length=30), nullable=True),
        ],
    )
    for table in ("planner_event", "schedule_series"):
        _create_columns(
            table,
            [
                sa.Column(
                    "artist_portal_visible",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.false(),
                )
            ],
        )

    bind = op.get_bind()
    for table, name, condition in (
        (
            "project",
            "ck_project_integration_kind",
            "integration_kind IS NULL OR integration_kind IN ('album', 'photoshoot', 'other')",
        ),
        (
            "task",
            "ck_task_artist_portal_kind",
            "artist_portal_kind IS NULL OR artist_portal_kind IN ('song', 'milestone')",
        ),
        (
            "task",
            "ck_task_integration_kind",
            "integration_kind IS NULL OR integration_kind = 'press_release'",
        ),
    ):
        constraints = {item["name"] for item in sa.inspect(bind).get_check_constraints(table)}
        if name not in constraints:
            with op.batch_alter_table(table) as batch:
                batch.create_check_constraint(name, condition)

    indexes = {
        (item["name"], tuple(item["column_names"]))
        for item in sa.inspect(bind).get_indexes("project")
    } if sa.inspect(bind).has_table("project") else set()
    if ("ix_project_bahandi_artist_id", ("bahandi_artist_id",)) not in indexes:
        op.create_index("ix_project_bahandi_artist_id", "project", ["bahandi_artist_id"])

    if not sa.inspect(bind).has_table("bahandi_feed_credential"):
        op.create_table(
            "bahandi_feed_credential",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("artist_id", sa.Integer(), nullable=False, unique=True),
            sa.Column("token_hash", sa.String(length=64), nullable=False, unique=True),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
    if not sa.inspect(bind).has_table("bahandi_press_outbox"):
        op.create_table(
            "bahandi_press_outbox",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("source_task_id", sa.String(length=50), nullable=False),
            sa.Column("source_submission_id", sa.String(length=50), nullable=False),
            sa.Column("payload", sa.JSON(), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="queued"),
            sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("run_at", sa.DateTime(), nullable=False),
            sa.Column("locked_at", sa.DateTime(), nullable=True),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.Column("last_error", sa.Text(), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("source_task_id", name="uq_bahandi_press_outbox_task"),
            sa.CheckConstraint(
                "status IN ('queued', 'processing', 'retrying', 'completed', 'failed')",
                name="ck_bahandi_press_outbox_status",
            ),
        )
        op.create_index(
            "ix_bahandi_press_outbox_status",
            "bahandi_press_outbox",
            ["status"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("bahandi_press_outbox"):
        op.drop_table("bahandi_press_outbox")
    if inspector.has_table("bahandi_feed_credential"):
        op.drop_table("bahandi_feed_credential")
    if inspector.has_table("project"):
        indexes = {item["name"] for item in sa.inspect(bind).get_indexes("project")}
        if "ix_project_bahandi_artist_id" in indexes:
            op.drop_index("ix_project_bahandi_artist_id", table_name="project")
        with op.batch_alter_table("project") as batch:
            constraints = {
                item["name"] for item in sa.inspect(bind).get_check_constraints("project")
            }
            if "ck_project_integration_kind" in constraints:
                batch.drop_constraint("ck_project_integration_kind", type_="check")
            for name in ("public_summary", "artist_portal_visible", "integration_kind", "bahandi_artist_id"):
                if name in _columns("project"):
                    batch.drop_column(name)
    if inspector.has_table("task"):
        constraints = {
            item["name"] for item in sa.inspect(bind).get_check_constraints("task")
        }
        with op.batch_alter_table("task") as batch:
            for name in ("ck_task_artist_portal_kind", "ck_task_integration_kind"):
                if name in constraints:
                    batch.drop_constraint(name, type_="check")
            for name in ("artist_portal_kind", "public_summary", "integration_kind"):
                if name in _columns("task"):
                    batch.drop_column(name)
    for table in ("planner_event", "schedule_series"):
        if "artist_portal_visible" in _columns(table):
            with op.batch_alter_table(table) as batch:
                batch.drop_column("artist_portal_visible")
