"""
Users Router
============
User display name resolution for created_by/last_modified_by fields.
"""
from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.framework.models.auth import User
from app.core.exceptions import ForbiddenError
from app.core.security import CurrentUser, is_system_admin_user, require_authenticated_user
from app.modules.workspaces.models import WorkspaceMembership
from app.modules.workspaces.services import WorkspaceService

router = APIRouter(prefix="/system/users", tags=["system-users"])


@router.get("/resolve-display-names")
async def resolve_user_display_names(
    user_ids: str = Query(..., description="Comma-separated list of user IDs to resolve"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_authenticated_user),
    workspace_id: str | None = Header(None, alias="X-Workspace-ID"),
):
    """
    Resolve user IDs to display names (full_name or username).

    Used for displaying created_by and last_modified_by fields in the UI.

    Query param: user_ids - comma-separated list of user IDs (e.g., "usr-001,usr-002")

    Returns: {user_id: display_name} mapping
    """
    # Parse user IDs
    ids = [uid.strip() for uid in user_ids.split(",") if uid.strip()][:100]
    if not ids:
        return {"status": "success", "data": {}}
    
    query = select(User).where(User.id.in_(ids))
    if not is_system_admin_user(current_user):
        context = await WorkspaceService.resolve_context(
            db,
            current_user.id,
            current_user.roles,
            current_user.is_superuser,
            workspace_id,
        )
        if not context.active_workspace_id:
            raise ForbiddenError("Use the paginated HR directory for global user lookup")
        role = await db.scalar(
            select(WorkspaceMembership.membership_role).where(
                WorkspaceMembership.workspace_id == context.active_workspace_id,
                WorkspaceMembership.user_id == current_user.id,
                WorkspaceMembership.is_active.is_(True),
            )
        )
        if role != "supervisor":
            raise ForbiddenError("Only workspace supervisors can resolve directory names")
        query = query.join(
            WorkspaceMembership, WorkspaceMembership.user_id == User.id
        ).where(
            WorkspaceMembership.workspace_id == context.active_workspace_id,
            WorkspaceMembership.is_active.is_(True),
        )
    result = await db.execute(query)
    users = result.scalars().all()
    
    # Build display name mapping
    display_names = {}
    for user in users:
        # Use full_name if available, fallback to username
        display_name = user.full_name if user.full_name else user.username
        display_names[user.id] = display_name
    
    # For any IDs not found, return the ID itself
    if is_system_admin_user(current_user):
        for uid in ids:
            if uid not in display_names:
                display_names[uid] = uid
    
    return {
        "status": "success",
        "data": display_names
    }
