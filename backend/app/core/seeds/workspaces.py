from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.seeds import SeedResult
from app.modules.workspaces.models import Workspace
from app.modules.workspaces.services import WORKSPACE_DEFAULTS, WorkspaceService


async def seed_workspaces(db: AsyncSession) -> SeedResult:
    result = SeedResult(entity="Workspaces")
    before = await db.scalar(select(func.count()).select_from(Workspace))
    await WorkspaceService.seed_defaults(db)
    after = await db.scalar(select(func.count()).select_from(Workspace))
    result.created = max((after or 0) - (before or 0), 0)
    result.skipped = max(len(WORKSPACE_DEFAULTS) - result.created, 0)
    return result
