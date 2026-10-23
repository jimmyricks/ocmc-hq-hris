from fastapi import APIRouter, Depends, Header, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4

from app.api.dependencies import get_db
from app.core.exceptions import BadRequestError, ConflictError, ForbiddenError, NotFoundError
from app.core.framework.models.auth import User
from app.core.security import CurrentUser, require_authenticated_user
from app.modules.project_tasks.models import Project, ProjectMember, Task, TaskType
from app.modules.workspaces.models import Workspace, WorkspaceMembership, WorkspaceTeam
from app.modules.workspaces.services import WorkspaceService
from app.modules.collaboration_audit.services import AuditLogService
from app.core.serialization import record_to_dict

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


class WorkspaceContextRequest(BaseModel):
    workspace_id: str | None = None


class WorkspaceUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    timezone: str | None = None
    is_active: bool | None = None


class MembershipRequest(BaseModel):
    user_id: str
    membership_role: str = "supervisor"
    is_home: bool = False


class WorkspaceTeamCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=100)


class LegacyMappingRequest(BaseModel):
    entity: str
    record_id: str
    workspace_id: str
    task_type_id: str | None = None


def _workspace_dict(workspace: Workspace) -> dict:
    return {
        "id": workspace.id,
        "name": workspace.name,
        "slug": workspace.slug,
        "color": workspace.color,
        "timezone": workspace.timezone,
        "is_active": workspace.is_active,
    }


def _require_admin(current_user: CurrentUser) -> None:
    if not WorkspaceService.is_system_admin(current_user.roles, current_user.is_superuser):
        raise ForbiddenError("Only HQ administrators can manage workspaces")


def _capabilities(
    current_user: CurrentUser,
    active_role: str | None,
    has_supervisor_membership: bool,
) -> dict[str, bool]:
    is_system_admin = WorkspaceService.is_system_admin(
        current_user.roles, current_user.is_superuser
    )
    return {
        "can_view_all_workspaces": is_system_admin,
        "can_manage_active_workspace": is_system_admin or active_role == "supervisor",
        "can_manage_payroll": WorkspaceService.is_payroll_admin(
            current_user.roles, current_user.is_superuser
        ),
        "can_view_global_schedule": is_system_admin or has_supervisor_membership,
        "can_view_hr_directory": is_system_admin
        or WorkspaceService.is_hr(current_user.roles),
        "is_system_admin": is_system_admin,
    }


@router.get("")
async def list_workspaces(
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
):
    await WorkspaceService.resolve_context(
        db,
        current_user.id,
        current_user.roles,
        current_user.is_superuser,
    )
    workspaces = await WorkspaceService.visible_workspaces(
        db, current_user.id, current_user.roles, current_user.is_superuser
    )
    return {"status": "success", "data": [_workspace_dict(workspace) for workspace in workspaces]}


@router.get("/context")
async def get_workspace_context(
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
    workspace_id: str | None = Header(None, alias="X-Workspace-ID"),
):
    return {
        "status": "success",
        "data": await WorkspaceService.get_context_payload(
            db,
            current_user,
            workspace_id,
        ),
    }


@router.get("/directory")
async def list_project_user_directory(
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
    workspace_id: str | None = Header(None, alias="X-Workspace-ID"),
    search: str | None = Query(None, min_length=1, max_length=100),
    project_id: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int | None = Query(None, ge=1, le=100),
):
    """List/search users, optionally scoped to active members of a project."""
    context = await WorkspaceService.resolve_context(
        db,
        current_user.id,
        current_user.roles,
        current_user.is_superuser,
        workspace_id,
    )
    is_system_admin = WorkspaceService.is_system_admin(
        current_user.roles, current_user.is_superuser
    )
    # HR may browse the global user directory (mirrors /hr-directory).
    is_hr = WorkspaceService.is_hr(current_user.roles)
    project = await db.get(Project, project_id) if project_id else None
    if project_id and (not project or not project.workspace_id):
        raise ForbiddenError("Project is unavailable in this workspace")

    is_workspace_supervisor = False
    if context.active_workspace_id:
        role = await db.scalar(
            select(WorkspaceMembership.membership_role).where(
                WorkspaceMembership.workspace_id == context.active_workspace_id,
                WorkspaceMembership.user_id == current_user.id,
                WorkspaceMembership.membership_role == "supervisor",
                WorkspaceMembership.is_active.is_(True),
            )
        )
        is_workspace_supervisor = role == "supervisor"

    if not is_system_admin and not is_hr:
        if project:
            project_member = await db.scalar(
                select(ProjectMember.id).where(
                    ProjectMember.project_id == project.id,
                    ProjectMember.user_id == current_user.id,
                    ProjectMember.is_active.is_(True),
                )
            )
            manages_workspace = (
                is_workspace_supervisor
                and context.active_workspace_id == project.workspace_id
            )
            if not manages_workspace and not project_member and (
                project.manager_id != current_user.id
            ):
                raise ForbiddenError("Project membership is required for this directory")
        elif not context.active_workspace_id or not is_workspace_supervisor:
            raise ForbiddenError(
                "Only workspace supervisors can browse the project directory"
            )
    user_query = select(User).where(User.is_active.is_(True))
    if project:
        user_query = (
            user_query.join(
                ProjectMember,
                (ProjectMember.user_id == User.id)
                & (ProjectMember.project_id == project_id)
                & (ProjectMember.is_active.is_(True)),
            )
            .distinct()
        )
    if search:
        pattern = f"%{search.strip()}%"
        user_query = user_query.where(
            User.full_name.ilike(pattern)
            | User.username.ilike(pattern)
            | User.email.ilike(pattern)
        )

    total = None
    if page_size is not None:
        total = await db.scalar(
            select(func.count()).select_from(user_query.order_by(None).subquery())
        )
        user_query = user_query.offset((page - 1) * page_size).limit(page_size)
    users = await db.scalars(user_query.order_by(User.full_name, User.username))
    result = {
        "status": "success",
        "data": [
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "is_active": user.is_active,
            }
            for user in users
        ],
    }
    if page_size is not None:
        result.update({"total": total or 0, "page": page, "page_size": page_size})
    return result


@router.get("/hr-directory")
async def list_hr_user_directory(
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
    page: int = 1,
    page_size: int = 50,
    search: str | None = None,
):
    is_system_admin = WorkspaceService.is_system_admin(
        current_user.roles, current_user.is_superuser
    )
    if not is_system_admin and not WorkspaceService.is_hr(current_user.roles):
        raise ForbiddenError("Only HR may view the global user directory")
    page_size = min(max(page_size, 1), 100)
    query = select(User).where(User.is_active.is_(True))
    if search:
        pattern = f"%{search.strip()}%"
        query = query.where(
            User.full_name.ilike(pattern)
            | User.username.ilike(pattern)
            | User.email.ilike(pattern)
        )
    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    users = await db.scalars(
        query.order_by(User.full_name, User.username)
        .offset((max(page, 1) - 1) * page_size)
        .limit(page_size)
    )
    return {
        "status": "success",
        "data": [
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "is_active": user.is_active,
            }
            for user in users
        ],
        "total": total,
        "page": max(page, 1),
        "page_size": page_size,
    }


@router.post("/context")
async def select_workspace_context(
    payload: WorkspaceContextRequest,
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
):
    context = await WorkspaceService.resolve_context(
        db,
        current_user.id,
        current_user.roles,
        current_user.is_superuser,
        payload.workspace_id,
    )
    active_role = (
        await db.scalar(
            select(WorkspaceMembership.membership_role).where(
                WorkspaceMembership.workspace_id == context.active_workspace_id,
                WorkspaceMembership.user_id == current_user.id,
                WorkspaceMembership.membership_role == "supervisor",
                WorkspaceMembership.is_active.is_(True),
            )
        )
        if context.active_workspace_id
        and not WorkspaceService.is_admin(current_user.roles, current_user.is_superuser)
        else None
    )
    memberships = (
        await db.scalars(
            select(WorkspaceMembership)
            .join(Workspace, Workspace.id == WorkspaceMembership.workspace_id)
            .where(
                WorkspaceMembership.user_id == current_user.id,
                WorkspaceMembership.membership_role == "supervisor",
                WorkspaceMembership.is_active.is_(True),
                Workspace.is_active.is_(True),
            )
        )
    ).all()
    memberships_by_workspace = {
        membership.workspace_id: membership for membership in memberships
    }
    workspaces = await WorkspaceService.visible_workspaces(
        db, current_user.id, current_user.roles, current_user.is_superuser
    )
    capabilities = _capabilities(
        current_user,
        active_role,
        any(item.membership_role == "supervisor" for item in memberships),
    )
    is_admin = capabilities["is_system_admin"]
    manageable_workspaces = [
        _workspace_dict(workspace)
        for workspace in workspaces
        if capabilities["is_system_admin"]
        or (
            memberships_by_workspace.get(workspace.id)
            and memberships_by_workspace[workspace.id].membership_role == "supervisor"
        )
    ]
    return {
        "status": "success",
        "data": {
            "active_workspace_id": context.active_workspace_id,
            "home_workspace_id": (
                await db.scalar(
                    select(WorkspaceMembership.workspace_id)
                    .join(Workspace, Workspace.id == WorkspaceMembership.workspace_id)
                    .where(
                        WorkspaceMembership.user_id == current_user.id,
                        WorkspaceMembership.membership_role == "supervisor",
                        WorkspaceMembership.is_home.is_(True),
                        WorkspaceMembership.is_active.is_(True),
                        Workspace.is_active.is_(True),
                    )
                )
            ),
            "is_global": context.is_global,
            "can_manage": capabilities["can_manage_active_workspace"],
            "capabilities": capabilities,
            "manageable_workspaces": manageable_workspaces,
        },
    }


@router.patch("/{workspace_id}")
async def update_workspace(
    workspace_id: str,
    payload: WorkspaceUpdateRequest,
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(current_user)
    workspace = await db.get(Workspace, workspace_id)
    if not workspace:
        raise NotFoundError("Workspace", workspace_id)

    old_values = record_to_dict(workspace)
    for field, value in payload.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(workspace, field, value)
    workspace.last_modified_by = current_user.id
    await AuditLogService.log_event(
        db,
        entity="workspace",
        record_id=workspace.id,
        action="update",
        actor_id=current_user.id,
        old_values=old_values,
        new_values=record_to_dict(workspace),
    )
    await db.commit()
    await db.refresh(workspace)
    return {"status": "success", "data": _workspace_dict(workspace)}


@router.get("/{workspace_id}/teams")
async def list_workspace_teams(
    workspace_id: str,
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
    requested_workspace_id: str | None = Header(None, alias="X-Workspace-ID"),
):
    context = await WorkspaceService.resolve_context(
        db,
        current_user.id,
        current_user.roles,
        current_user.is_superuser,
        requested_workspace_id or workspace_id,
    )
    if (
        not context.is_global
        and context.active_workspace_id != workspace_id
    ):
        raise ForbiddenError("You cannot view teams for this workspace")
    result = await db.execute(
        select(WorkspaceTeam)
        .where(WorkspaceTeam.workspace_id == workspace_id)
        .order_by(WorkspaceTeam.name)
    )
    return {
        "status": "success",
        "data": [
            {"id": team.id, "workspace_id": team.workspace_id, "name": team.name, "slug": team.slug}
            for team in result.scalars().all()
        ],
    }


@router.post("/{workspace_id}/teams")
async def create_workspace_team(
    workspace_id: str,
    payload: WorkspaceTeamCreate,
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(current_user)
    workspace = await db.get(Workspace, workspace_id)
    if not workspace or not workspace.is_active:
        raise NotFoundError("Workspace", workspace_id)
    team = WorkspaceTeam(
        id=str(uuid4()),
        workspace_id=workspace_id,
        name=payload.name,
        slug=payload.slug,
        created_by=current_user.id,
        last_modified_by=current_user.id,
    )
    db.add(team)
    await db.flush()
    await AuditLogService.log_event(
        db,
        entity="workspace_team",
        record_id=team.id,
        action="create",
        actor_id=current_user.id,
        old_values=None,
        new_values=record_to_dict(team),
    )
    await db.commit()
    return {
        "status": "success",
        "data": {"id": team.id, "workspace_id": team.workspace_id, "name": team.name, "slug": team.slug},
    }


@router.get("/unmapped")
async def list_unmapped_records(
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(current_user)
    projects = (
        await db.scalars(select(Project).where(Project.workspace_id.is_(None)).order_by(Project.name))
    ).all()
    task_types = (
        await db.scalars(
            select(TaskType).where(TaskType.workspace_id.is_(None)).order_by(TaskType.name)
        )
    ).all()
    tasks = (
        await db.execute(
            select(Task, Project, TaskType)
            .outerjoin(Project, Project.id == Task.project_id)
            .outerjoin(TaskType, TaskType.id == Task.task_type_id)
            .where(
                (Task.workspace_id.is_(None))
                | (Task.workspace_id != Project.workspace_id)
                | (
                    Task.task_type_id.is_not(None)
                    & (
                        TaskType.workspace_id.is_(None)
                        | (TaskType.workspace_id != Project.workspace_id)
                    )
                )
            )
            .order_by(Task.title, Task.id)
        )
    ).all()
    return {
        "status": "success",
        "data": {
            "projects": [{"id": row.id, "name": row.name} for row in projects],
            "task_types": [
                {
                    "id": row.id,
                    "name": row.name,
                    "unit_rate": float(row.unit_rate or 0),
                    "unit": row.unit,
                }
                for row in task_types
            ],
            "tasks": [
                {
                    "id": task.id,
                    "title": task.title,
                    "project_id": task.project_id,
                    "project_workspace_id": project.workspace_id if project else None,
                    "task_type_id": task.task_type_id,
                    "task_type_workspace_id": (
                        task_type.workspace_id if task_type else None
                    ),
                    "workspace_id": task.workspace_id,
                }
                for task, project, task_type in tasks
            ],
        },
    }


@router.post("/map-legacy")
async def map_legacy_record(
    payload: LegacyMappingRequest,
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(current_user)
    workspace = await db.get(Workspace, payload.workspace_id)
    if not workspace or not workspace.is_active:
        raise NotFoundError("Workspace", payload.workspace_id)

    models = {
        "project": Project,
        "task_type": TaskType,
        "task": Task,
    }
    model = models.get(payload.entity)
    if not model:
        raise BadRequestError("Only projects, task types, and tasks can be mapped")
    record = await db.get(model, payload.record_id)
    if not record:
        raise NotFoundError(payload.entity, payload.record_id)
    if payload.entity == "task":
        project = await db.get(Project, record.project_id)
        task_type_id = payload.task_type_id or record.task_type_id
        task_type = await db.get(TaskType, task_type_id) if task_type_id else None
        if not project or project.workspace_id != workspace.id:
            raise ConflictError("Task project must belong to the selected workspace")
        if task_type_id and (
            not task_type or task_type.workspace_id != workspace.id
        ):
            raise ConflictError(
                "Task type must belong to the selected workspace"
            )
        if record.workspace_id == workspace.id and record.task_type_id == task_type_id:
            raise ConflictError("This task already belongs to the selected workspace")
    elif record.workspace_id == workspace.id:
        raise ConflictError("This record already belongs to a workspace")
    elif payload.entity == "project":
        task_types = await db.scalars(
            select(TaskType)
            .join(Task, Task.task_type_id == TaskType.id)
            .where(Task.project_id == record.id)
        )
        if any(task_type.workspace_id != workspace.id for task_type in task_types):
            raise ConflictError(
                "Map or replace task types before assigning this project to that workspace"
            )
    elif payload.entity == "task_type":
        project_workspace_ids = await db.scalars(
            select(Project.workspace_id)
            .join(Task, Task.project_id == Project.id)
            .where(
                Task.task_type_id == record.id,
                Project.workspace_id.is_not(None),
            )
            .distinct()
        )
        if any(workspace_id != workspace.id for workspace_id in project_workspace_ids):
            raise ConflictError(
                "This task type is used by projects in another workspace; create a workspace-specific rate instead"
            )

    old_values = record_to_dict(record)
    record.workspace_id = workspace.id
    if payload.entity == "task" and payload.task_type_id:
        record.task_type_id = payload.task_type_id
    record.last_modified_by = current_user.id
    await db.flush()

    if payload.entity == "project":
        tasks = await db.scalars(select(Task).where(Task.project_id == record.id))
        for task in tasks:
            task_old_values = record_to_dict(task)
            task.workspace_id = workspace.id
            task.last_modified_by = current_user.id
            await AuditLogService.log_event(
                db,
                entity="task",
                record_id=task.id,
                action="update",
                actor_id=current_user.id,
                old_values=task_old_values,
                new_values=record_to_dict(task),
            )
    elif payload.entity == "task_type":
        tasks = await db.scalars(
            select(Task)
            .join(Project, Project.id == Task.project_id)
            .where(
                Task.task_type_id == record.id,
                Project.workspace_id == workspace.id,
            )
        )
        for task in tasks:
            task_old_values = record_to_dict(task)
            task.workspace_id = workspace.id
            task.last_modified_by = current_user.id
            await AuditLogService.log_event(
                db,
                entity="task",
                record_id=task.id,
                action="update",
                actor_id=current_user.id,
                old_values=task_old_values,
                new_values=record_to_dict(task),
            )
    await AuditLogService.log_event(
        db,
        entity=payload.entity,
        record_id=record.id,
        action="update",
        actor_id=current_user.id,
        old_values=old_values,
        new_values=record_to_dict(record),
    )
    await db.commit()
    return {
        "status": "success",
        "data": {"entity": payload.entity, "id": record.id, "workspace_id": workspace.id},
    }


@router.get("/{workspace_id}/memberships")
async def list_workspace_memberships(
    workspace_id: str,
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
    requested_workspace_id: str | None = Header(None, alias="X-Workspace-ID"),
):
    context = await WorkspaceService.resolve_context(
        db,
        current_user.id,
        current_user.roles,
        current_user.is_superuser,
        requested_workspace_id or workspace_id,
    )
    if (
        not WorkspaceService.is_admin(current_user.roles, current_user.is_superuser)
        and context.active_workspace_id != workspace_id
    ):
        raise ForbiddenError("You cannot view memberships for this workspace")
    if not WorkspaceService.is_admin(
        current_user.roles, current_user.is_superuser
    ):
        role = await db.scalar(
            select(WorkspaceMembership.membership_role).where(
                WorkspaceMembership.workspace_id == workspace_id,
                WorkspaceMembership.user_id == current_user.id,
                WorkspaceMembership.is_active.is_(True),
            )
        )
        if role != "supervisor":
            raise ForbiddenError("Only workspace supervisors can view memberships")
    result = await db.execute(
        select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == workspace_id,
            WorkspaceMembership.membership_role == "supervisor",
            WorkspaceMembership.is_active.is_(True),
        )
    )
    return {
        "status": "success",
        "data": [
            {
                "id": item.id,
                "workspace_id": item.workspace_id,
                "user_id": item.user_id,
                "membership_role": item.membership_role,
                "is_home": item.is_home,
            }
            for item in result.scalars().all()
        ],
    }


@router.post("/{workspace_id}/memberships")
async def assign_workspace_membership(
    workspace_id: str,
    payload: MembershipRequest,
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(current_user)
    membership = await WorkspaceService.assign_membership(
        db,
        workspace_id,
        payload.user_id,
        payload.membership_role,
        payload.is_home,
        current_user.id,
    )
    return {
        "status": "success",
        "data": {
            "id": membership.id,
            "workspace_id": membership.workspace_id,
            "user_id": membership.user_id,
            "membership_role": membership.membership_role,
            "is_home": membership.is_home,
            "is_active": membership.is_active,
        },
    }


@router.delete("/{workspace_id}/memberships/{membership_id}")
async def remove_workspace_membership(
    workspace_id: str,
    membership_id: str,
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(current_user)
    membership = await db.get(WorkspaceMembership, membership_id)
    if not membership or membership.workspace_id != workspace_id:
        raise NotFoundError("Workspace membership", membership_id)
    old_values = record_to_dict(membership)
    membership.is_active = False
    membership.is_home = False
    membership.last_modified_by = current_user.id
    await AuditLogService.log_event(
        db,
        entity="workspace_membership",
        record_id=membership.id,
        action="update",
        actor_id=current_user.id,
        old_values=old_values,
        new_values=record_to_dict(membership),
    )
    await db.commit()
    return {"status": "success", "message": "Workspace membership deactivated"}
