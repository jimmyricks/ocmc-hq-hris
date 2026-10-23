import asyncio
from pathlib import Path

import pytest
from sqlalchemy import Boolean, Column, Date, DateTime, MetaData, String, Table, inspect, text
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import command
from alembic.config import Config

import app.core.database as database


@pytest.mark.asyncio
async def test_workspace_migrations_align_the_legacy_schema_for_seeders(
    tmp_path, monkeypatch
):
    db_path = tmp_path / "legacy.sqlite"
    async_url = f"sqlite+aiosqlite:///{db_path}"
    sync_url = f"sqlite:///{db_path}"
    legacy_engine = create_async_engine(async_url)

    def create_pre_workspace_schema(connection):
        metadata = MetaData()
        Table(
            "alembic_version",
            metadata,
            Column("version_num", String(32), primary_key=True),
        )
        Table(
            "workspace",
            metadata,
            Column("id", String(50), primary_key=True),
            Column("name", String(255), nullable=True),
            Column("slug", String(255), nullable=True),
            Column("color", String(255), nullable=True),
            Column("timezone", String(255), nullable=True),
            Column("is_active", Boolean, nullable=True),
        )
        Table(
            "workspace_team",
            metadata,
            Column("id", String(50), primary_key=True),
            Column("workspace_id", String(50), nullable=True),
            Column("name", String(255), nullable=True),
            Column("slug", String(255), nullable=True),
        )
        Table(
            "planner_event",
            metadata,
            Column("id", String(50), primary_key=True),
            Column("workspace_id", String(50), nullable=False),
        )
        Table(
            "schedule_series",
            metadata,
            Column("id", String(50), primary_key=True),
            Column("workspace_id", String(50), nullable=False),
        )
        Table(
            "project",
            metadata,
            Column("id", String(50), primary_key=True),
            Column("workspace_id", String(50)),
            Column("team_id", String(50)),
            Column("start_date", Date(), nullable=True),
            Column("end_date", Date(), nullable=True),
        )
        Table(
            "task_type",
            metadata,
            Column("id", String(50), primary_key=True),
            Column("workspace_id", String(50)),
        )
        Table(
            "task",
            metadata,
            Column("id", String(50), primary_key=True),
            Column("project_id", String(50)),
            Column("task_type_id", String(50)),
            Column("planned_start_at", DateTime(), nullable=True),
            Column("planned_end_at", DateTime(), nullable=True),
            Column("due_date", DateTime(), nullable=True),
        )
        Table(
            "core_users",
            metadata,
            Column("id", String(36), primary_key=True),
        )
        Table(
            "task_submission",
            metadata,
            Column("id", String(50), primary_key=True),
            Column("status", String(100), nullable=True),
        )
        Table(
            "payroll_entry",
            metadata,
            Column("id", String(50), primary_key=True),
        )
        Table(
            "invoice",
            metadata,
            Column("id", String(50), primary_key=True),
            Column("payroll_entry_id", String(50), nullable=True),
        )
        Table(
            "payroll_line_item",
            metadata,
            Column("id", String(50), primary_key=True),
            Column("workspace_id", String(50)),
        )
        metadata.create_all(connection)
        connection.execute(
            text(
                """
                INSERT INTO workspace (id, name, slug, color, timezone, is_active)
                VALUES
                    ('workspace-a', 'Workspace A', 'workspace-a', '#112233', 'UTC', 1),
                    ('workspace-b', 'Workspace B', 'workspace-b', '#445566', 'UTC', 1)
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO project (id, workspace_id, team_id)
                VALUES ('project-a', 'workspace-a', NULL)
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO task_type (id, workspace_id)
                VALUES ('type-a', 'workspace-a'), ('type-b', 'workspace-b')
                """
            )
        )
        connection.execute(
            text(
                """
                    INSERT INTO task (id, project_id, task_type_id, planned_start_at, planned_end_at)
                VALUES
                    ('task-mapped', 'project-a', 'type-a', NULL, NULL),
                    ('task-mismatched-type', 'project-a', 'type-b', NULL, NULL)
                """
            )
        )
        connection.execute(
            text("INSERT INTO alembic_version (version_num) VALUES ('1aaef8fe765b')")
        )

    async with legacy_engine.begin() as connection:
        await connection.run_sync(create_pre_workspace_schema)

    monkeypatch.setattr(database, "engine", legacy_engine)
    monkeypatch.setattr(database.settings, "DATABASE_URL_SYNC", sync_url)
    try:
        backend_dir = Path(__file__).resolve().parents[2]

        def apply_migration():
            config = Config(str(backend_dir / "alembic.ini"))
            config.set_main_option("script_location", str(backend_dir / "alembic"))
            config.set_main_option("sqlalchemy.url", sync_url)
            command.upgrade(config, "head")

        await asyncio.to_thread(apply_migration)
        await database.verify_workspace_schema()

        async with legacy_engine.connect() as connection:
            columns = await connection.run_sync(
                lambda sync_connection: {
                    column["name"]
                    for column in inspect(sync_connection).get_columns("task_type")
                }
            )
            task_columns = await connection.run_sync(
                lambda sync_connection: {
                    column["name"]
                    for column in inspect(sync_connection).get_columns("task")
                }
            )
            task_ownership = await connection.execute(
                text(
                    "SELECT id, workspace_id FROM task ORDER BY id"
                )
            )
            task_ownership = task_ownership.all()
            task_foreign_keys = await connection.run_sync(
                lambda sync_connection: {
                    foreign_key.get("name")
                    for foreign_key in inspect(sync_connection).get_foreign_keys("task")
                }
            )
            project_columns = await connection.run_sync(
                lambda sync_connection: {
                    column["name"]
                    for column in inspect(sync_connection).get_columns("project")
                }
            )
            revision = await connection.scalar(
                text("SELECT version_num FROM alembic_version")
            )

        assert "workspace_id" in columns
        assert "workspace_id" in task_columns
        assert task_ownership == [
            ("task-mapped", "workspace-a"),
            ("task-mismatched-type", None),
        ]
        assert {
            "fk_task_workspace",
            "fk_task_project_workspace",
            "fk_task_task_type_workspace",
        }.issubset(task_foreign_keys)
        assert "is_continuous" in project_columns
        assert "planned_start_at" not in task_columns
        assert "planned_end_at" not in task_columns
        assert revision == "20261103_ws_task_workflows"
    finally:
        await legacy_engine.dispose()


@pytest.mark.asyncio
async def test_project_schedule_migration_moves_planned_task_bounds_to_projects():
    import importlib.util
    from datetime import date, datetime

    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy import Date, DateTime, select

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    def upgrade_and_read(connection):
        metadata = MetaData()
        project = Table(
            "project",
            metadata,
            Column("id", String(50), primary_key=True),
            Column("start_date", Date(), nullable=True),
            Column("end_date", Date(), nullable=True),
        )
        task = Table(
            "task",
            metadata,
            Column("id", String(50), primary_key=True),
            Column("project_id", String(50)),
            Column("planned_start_at", DateTime(), nullable=True),
            Column("planned_end_at", DateTime(), nullable=True),
            Column("due_date", DateTime(), nullable=True),
        )
        metadata.create_all(connection)
        connection.execute(
            project.insert(),
            [
                {"id": "project-empty", "start_date": None, "end_date": None},
                {
                    "id": "project-existing",
                    "start_date": date(2026, 1, 1),
                    "end_date": date(2026, 1, 31),
                },
            ],
        )
        connection.execute(
            task.insert(),
            [
                {
                    "id": "task-first",
                    "project_id": "project-empty",
                    "planned_start_at": datetime(2026, 2, 10),
                    "planned_end_at": datetime(2026, 2, 12),
                    "due_date": datetime(2026, 2, 11),
                },
                {
                    "id": "task-second",
                    "project_id": "project-empty",
                    "planned_start_at": datetime(2026, 2, 8),
                    "planned_end_at": datetime(2026, 2, 14),
                    "due_date": None,
                },
                {
                    "id": "task-existing-project",
                    "project_id": "project-existing",
                    "planned_start_at": datetime(2026, 3, 1),
                    "planned_end_at": datetime(2026, 3, 30),
                    "due_date": None,
                },
            ],
        )

        migration_path = (
            Path(__file__).resolve().parents[2]
            / "alembic"
            / "versions"
            / "20261023_project_schedule.py"
        )
        spec = importlib.util.spec_from_file_location(
            "project_schedule_migration", migration_path
        )
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()

        project_after = Table("project", MetaData(), autoload_with=connection)
        task_after = Table("task", MetaData(), autoload_with=connection)
        projects = connection.execute(
            select(
                project_after.c.id,
                project_after.c.start_date,
                project_after.c.end_date,
                project_after.c.is_continuous,
            ).order_by(project_after.c.id)
        ).all()
        task_columns = {
            column["name"] for column in inspect(connection).get_columns("task")
        }
        return projects, task_columns

    try:
        async with engine.begin() as connection:
            projects, task_columns = await connection.run_sync(upgrade_and_read)
        assert projects == [
            ("project-empty", date(2026, 2, 8), date(2026, 2, 14), False),
            ("project-existing", date(2026, 1, 1), date(2026, 1, 31), False),
        ]
        assert "planned_start_at" not in task_columns
        assert "planned_end_at" not in task_columns
        assert "due_date" in task_columns
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_untracked_legacy_schema_reports_missing_workspace_columns(
    tmp_path, monkeypatch
):
    legacy_engine = create_async_engine(
        f"sqlite+aiosqlite:///{tmp_path / 'untracked.sqlite'}"
    )

    def create_legacy_tables(connection):
        metadata = MetaData()
        for table_name in ("project", "task_type", "task", "payroll_line_item"):
            Table(
                table_name,
                metadata,
                Column("id", String(50), primary_key=True),
                Column("name", String(255)),
            )
        metadata.create_all(connection)

    async with legacy_engine.begin() as connection:
        await connection.run_sync(create_legacy_tables)

    monkeypatch.setattr(database, "engine", legacy_engine)
    try:
        with pytest.raises(
            RuntimeError,
            match="task_type\\(workspace_id\\).*no Alembic version marker",
        ):
            await database.verify_workspace_schema()
    finally:
        await legacy_engine.dispose()


@pytest.mark.asyncio
async def test_project_schedule_migration_moves_task_bounds_and_drops_task_columns():
    from datetime import date, datetime
    import importlib.util

    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy import Date, DateTime, select

    from pathlib import Path

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    def migrate_and_read(connection):
        metadata = MetaData()
        project = Table(
            "project",
            metadata,
            Column("id", String(50), primary_key=True),
            Column("start_date", Date(), nullable=True),
            Column("end_date", Date(), nullable=True),
        )
        task = Table(
            "task",
            metadata,
            Column("id", String(50), primary_key=True),
            Column("project_id", String(50), nullable=True),
            Column("planned_start_at", DateTime(), nullable=True),
            Column("planned_end_at", DateTime(), nullable=True),
            Column("due_date", DateTime(), nullable=True),
        )
        metadata.create_all(connection)
        connection.execute(
            project.insert(),
            [
                {"id": "project-empty", "start_date": None, "end_date": None},
                {
                    "id": "project-existing",
                    "start_date": date(2026, 1, 1),
                    "end_date": date(2026, 1, 31),
                },
            ],
        )
        connection.execute(
            task.insert(),
            [
                {
                    "id": "task-first",
                    "project_id": "project-empty",
                    "planned_start_at": datetime(2026, 2, 10),
                    "planned_end_at": datetime(2026, 2, 12),
                    "due_date": datetime(2026, 2, 11),
                },
                {
                    "id": "task-second",
                    "project_id": "project-empty",
                    "planned_start_at": datetime(2026, 2, 8),
                    "planned_end_at": datetime(2026, 2, 14),
                    "due_date": None,
                },
                {
                    "id": "task-existing-project",
                    "project_id": "project-existing",
                    "planned_start_at": datetime(2026, 3, 1),
                    "planned_end_at": datetime(2026, 3, 30),
                    "due_date": None,
                },
            ],
        )

        migration_path = (
            Path(__file__).resolve().parents[2]
            / "alembic"
            / "versions"
            / "20261023_project_schedule.py"
        )
        spec = importlib.util.spec_from_file_location(
            "project_schedule_migration", migration_path
        )
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()

        updated_project = Table("project", MetaData(), autoload_with=connection)
        updated_task = Table("task", MetaData(), autoload_with=connection)
        project_dates = connection.execute(
            select(
                updated_project.c.id,
                updated_project.c.start_date,
                updated_project.c.end_date,
                updated_project.c.is_continuous,
            ).order_by(updated_project.c.id)
        ).all()
        task_columns = {column["name"] for column in inspect(connection).get_columns("task")}
        return project_dates, task_columns

    try:
        async with engine.begin() as connection:
            project_dates, task_columns = await connection.run_sync(migrate_and_read)
        assert project_dates == [
            ("project-empty", date(2026, 2, 8), date(2026, 2, 14), False),
            ("project-existing", date(2026, 1, 1), date(2026, 1, 31), False),
        ]
        assert "planned_start_at" not in task_columns
        assert "planned_end_at" not in task_columns
        assert "due_date" in task_columns
    finally:
        await engine.dispose()
