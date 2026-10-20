"""Seed the built-in task type catalog from canonical workspace constants."""

from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import TASK_TYPES
from app.core.seeds import SeedResult
from app.modules.project_tasks.models import TaskType
from app.modules.workspaces.models import Workspace
from app.modules.workspaces.services import WorkspaceService


async def seed_task_types(db: AsyncSession) -> SeedResult:
    result = SeedResult(entity="Task Types")
    await WorkspaceService.seed_defaults(db)
    workspaces = (
        await db.execute(select(Workspace).where(Workspace.is_active.is_(True)))
    ).scalars().all()

    for workspace in workspaces:
        for name in TASK_TYPES:
            existing = await db.execute(
                select(TaskType.id).where(
                    func.lower(TaskType.name) == name.lower(),
                    TaskType.workspace_id == workspace.id,
                )
            )
            if existing.scalar_one_or_none():
                result.skipped += 1
                continue

            db.add(
                TaskType(
                    id=str(
                        uuid5(
                            NAMESPACE_URL,
                            f"ocmc-hq/task-type/{workspace.slug}/{name.lower()}",
                        )
                    ),
                    workspace_id=workspace.id,
                    name=name,
                    description="Built-in task type.",
                    unit_rate=0,
                    unit="per_deliverable",
                    requires_approval=True,
                )
            )
            result.created += 1

    if result.created:
        await db.commit()
    return result
