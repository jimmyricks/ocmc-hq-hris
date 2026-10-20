import asyncio

from app.core.constants import (
    DEFAULT_TASK_PRIORITY,
    OFFICIAL_CURRENCY,
    TASK_PRIORITIES,
    TASK_TYPES,
    WORKSPACE_ROLES,
)
from app.core.seeds.task_types import seed_task_types
from app.modules.payroll.models import Invoice, PayrollSettings


class _SeedResult:
    def __init__(self, exists: bool):
        self.exists = exists

    def scalar_one_or_none(self):
        return object() if self.exists else None


class _TaskTypeSeedSession:
    def __init__(self):
        self.names: set[str] = set()
        self.added = []
        self.commits = 0

    async def execute(self, _statement):
        return _SeedResult(bool(self.names))

    def add(self, record):
        self.added.append(record)

    async def commit(self):
        self.commits += 1
        self.names.update(record.name.lower() for record in self.added)


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
    assert db.commits == 1
