"""
Core Layer: Database Setup

SQLAlchemy async engine, session factory, and Base model.

Clean Architecture Layer: Core
Responsibility: Provide database connection and ORM configuration
"""
import time
import logging

from sqlalchemy import event, inspect
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

slow_query_logger = logging.getLogger("slow_queries")

_is_sqlite = "sqlite" in settings.DATABASE_URL

_pool_kwargs = (
    {}
    if _is_sqlite
    else {
        "pool_size": settings.DB_POOL_SIZE,
        "max_overflow": settings.DB_MAX_OVERFLOW,
        "pool_recycle": settings.DB_POOL_RECYCLE,
        "pool_pre_ping": True,
    }
)

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DB_ECHO,
    **_pool_kwargs,
)

# ---------------------------------------------------------------------------
# Slow-query event listeners (logs any query taking >100ms) - DISABLED
# ---------------------------------------------------------------------------
# @event.listens_for(engine.sync_engine, "before_cursor_execute")
# def _before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
#     conn.info.setdefault("query_start_time", []).append(time.time())

# @event.listens_for(engine.sync_engine, "after_cursor_execute")
# def _after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
#     total = time.time() - conn.info["query_start_time"].pop(-1)
#     if total > 0.1:  # 100ms threshold
#         slow_query_logger.warning(
#             "SLOW QUERY (%dms):\n%s\nParams: %s", int(total * 1000), statement, parameters
#         )

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def verify_workspace_schema() -> None:
    """Fail before create_all/seeders obscure an unapplied workspace migration."""
    required_columns = {
        "project": {"workspace_id", "team_id", "is_continuous"},
        "task": {"workspace_id"},
        "task_type": {"workspace_id"},
        "payroll_line_item": {"workspace_id"},
    }
    async with engine.connect() as conn:
        schema_state = await conn.run_sync(
            lambda sync_conn: (
                set(inspect(sync_conn).get_table_names()),
                inspect(sync_conn).has_table("alembic_version"),
            )
        )
        tables, is_versioned = schema_state
        if not tables.intersection(required_columns):
            return
        missing = await conn.run_sync(
            lambda sync_conn: {
                table_name: sorted(
                    column_name
                    for column_name in columns
                    if column_name
                    not in {
                        column["name"]
                        for column in inspect(sync_conn).get_columns(table_name)
                    }
                )
                for table_name, columns in required_columns.items()
                if table_name in tables
            }
        )

    missing = {table: columns for table, columns in missing.items() if columns}
    if missing:
        details = ", ".join(
            f"{table}({', '.join(columns)})"
            for table, columns in sorted(missing.items())
        )
        if is_versioned:
            remediation = "Run `cd backend && .venv/bin/alembic upgrade head`."
        else:
            remediation = (
                "This legacy database has no Alembic version marker; verify its "
                "baseline before applying or stamping migrations."
            )
        raise RuntimeError(
            f"Database schema is behind the workspace/project schedule migrations: {details}. "
            f"{remediation}"
        )
