import asyncio
from types import SimpleNamespace

from app.core.constants import (
    DEFAULT_TASK_PRIORITY,
    OFFICIAL_CURRENCY,
    TASK_PRIORITIES,
    TASK_TYPES,
    WORKSPACE_ROLES,
)
from app.core.seeds.task_types import seed_task_types
from app.modules.payroll.models import Invoice, PayrollSettings
from app.modules.project_tasks.models import TaskType
from app.modules.workspaces.models import Workspace


class _SeedResult:
    def __init__(self, exists: bool):
        self.exists = exists

    def scalar_one_or_none(self):
        return object() if self.exists else None


class _WorkspaceResult:
    def __init__(self, workspaces):
        self._workspaces = workspaces

    def scalars(self):
        return self

    def all(self):
        return self._workspaces


class _TaskTypeSeedSession:
    def __init__(self):
        self.names: set[str] = set()
        self.added = []
        self.commits = 0
        self._workspace = SimpleNamespace(id="ws-1", slug="ws-1", is_active=True)

    async def execute(self, statement):
        entities = {d.get("entity") for d in statement.column_descriptions}
        if Workspace in entities:
            return _WorkspaceResult([self._workspace])
        return _SeedResult(bool(self.names))

    async def scalar(self, _statement):
        return None

    async def flush(self):
        pass

    def add(self, record):
        self.added.append(record)

    async def commit(self):
        self.commits += 1
        self.names.update(
            record.name.lower() for record in self.added if isinstance(record, TaskType)
        )


def test_workspace_catalog_values_are_canonical():
    assert TASK_TYPES == ("Reel", "Poster", "Caption", "Pitch Deck", "other")
    assert TASK_PRIORITIES == ("low", "medium", "high", "urgent")
    assert DEFAULT_TASK_PRIORITY == "medium"
    assert WORKSPACE_ROLES == (
        "project manager",
        "user/member",
        "supervisor",
        "system administrator",
    )
    assert OFFICIAL_CURRENCY == "PHP"
    assert PayrollSettings.__table__.c.currency.default.arg == OFFICIAL_CURRENCY
    assert Invoice.__table__.c.currency.default.arg == OFFICIAL_CURRENCY


def test_task_type_seed_is_idempotent():
    db = _TaskTypeSeedSession()

    first_run = asyncio.run(seed_task_types(db))
    second_run = asyncio.run(seed_task_types(db))

    assert first_run.created == len(TASK_TYPES)
    assert second_run.created == 0
    assert second_run.skipped == len(TASK_TYPES)
    task_types_added = [r for r in db.added if isinstance(r, TaskType)]
    assert len(task_types_added) == len(TASK_TYPES)
    assert db.commits >= 1
