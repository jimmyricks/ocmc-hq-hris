import asyncio
from pathlib import Path

import pytest
from sqlalchemy import Boolean, Column, MetaData, String, Table, inspect, text
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
            Column("planned_start_at", String(50)),
            Column("planned_end_at", String(50)),
        )
        Table(
            "payroll_line_item",
            metadata,
            Column("id", String(50), primary_key=True),
            Column("workspace_id", String(50)),
        )
        metadata.create_all(connection)
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
            revision = await connection.scalar(
                text("SELECT version_num FROM alembic_version")
            )

        assert "workspace_id" in columns
        assert revision == "20261021_workspace_schema"
    finally:
        await legacy_engine.dispose()


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
