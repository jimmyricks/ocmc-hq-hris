"""
Project & Task Management app endpoints.

Higher-level routes for task creation, assignment, and assignment listing.
Entities project and task_type are intentionally managed through the generic
entity CRUD kernel; this module exposes the task-specific workflow helpers.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, Header, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, get_rbac_service, get_row_scope_service
from app.application.services.access_control.rbac_service import RBACAppService
from app.application.services.access_control.row_scope_service import RowScopeService
from app.core.exceptions import ForbiddenError
from app.core.framework.models.auth import User
from app.core.security import require_authenticated_user, CurrentUser
from app.core.serialization import record_to_dict
from app.application.email_notifications.task_assignment import (
    send_task_assignment_email,
)
from app.modules.project_tasks.services import (
    ProjectTaskService,
    TaskApprovalService,
    TaskSubmissionService,
)
from app.modules.project_tasks.models import (
    Project,
    ProjectMember,
    Task,
    TaskAssignment,
    TaskLink,
    TaskSubmission,
    TaskType,
)
from app.modules.workspaces.models import Workspace, WorkspaceMembership
from app.modules.workspaces.services import WorkspaceService
from app.schemas.base import ActionResponse

router = APIRouter(prefix="/project-tasks", tags=["project-tasks"])


class CreateTaskRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    project_id: str
    task_type_id: str
    title: str
    description: str | None = None
    priority: str = "medium"
    due_date: datetime | None = None
    status: str = "pending"


class AssignTaskRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    user_id: str


class CreateSubmissionRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    task_assignment_id: str
    notes: str | None = None
    external_link: str | None = None
    content: str | None = None
    previous_submission_id: str | None = None


class CreateApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    decision: str
    remarks: str | None = None


class TaskSummariesRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    task_ids: list[str]


async def _check_permission(
    current_user: CurrentUser,
    rbac: RBACAppService,
    entity: str,
    action: str,
) -> None:
    allowed = await rbac.check_permission(
        user_id=current_user.id,
        entity=entity,
        action=action,
        role_ids=current_user.role_ids,
        is_superuser=current_user.is_superuser,
    )
    if not allowed:
        raise ForbiddenError(f"You don't have permission to {action} {entity}")


async def _check_workspace_supervisor(
    current_user: CurrentUser,
    rbac: RBACAppService,
    db: AsyncSession,
    entity: str,
    action: str,
    workspace_id: str,
    requested_workspace_id: str | None,
) -> None:
    await WorkspaceService.require_workspace_role(
        db,
        current_user,
        workspace_id,
        "supervisor",
        requested_workspace_id,
    )
    allowed = await rbac.check_permission(
        user_id=current_user.id,
        entity=entity,
        action=action,
        role_ids=current_user.role_ids,
        is_superuser=current_user.is_superuser,
    )
    if not allowed and WorkspaceService.is_admin(
        current_user.roles, current_user.is_superuser
    ):
        raise ForbiddenError(f"You don't have permission to {action} {entity}")


async def _check_task_creator(
    current_user: CurrentUser,
    db: AsyncSession,
    project: Project,
    requested_workspace_id: str | None,
) -> None:
    context = await WorkspaceService.resolve_context(
        db,
        current_user.id,
        current_user.roles,
        current_user.is_superuser,
        requested_workspace_id,
    )
    if WorkspaceService.is_admin(
        current_user.roles, current_user.is_superuser
    ):
        return
    if project.workspace_id != context.active_workspace_id:
        raise ForbiddenError("Tasks are limited to the active workspace")

    if await db.scalar(
        select(WorkspaceMembership.id).where(
            WorkspaceMembership.workspace_id == project.workspace_id,
            WorkspaceMembership.user_id == current_user.id,
            WorkspaceMembership.membership_role == "supervisor",
            WorkspaceMembership.is_active.is_(True),
        )
    ):
        return
    raise ForbiddenError("Project membership is required to create tasks")


async def _check_project_membership_manager(
    current_user: CurrentUser,
    db: AsyncSession,
    project: Project,
    requested_workspace_id: str | None,
) -> None:
    await WorkspaceService.require_workspace_role(
        db,
        current_user,
        project.workspace_id,
        "supervisor",
        requested_workspace_id,
    )


async def _check_submission_reviewer(
    current_user: CurrentUser,
    rbac: RBACAppService,
    db: AsyncSession,
    project: Project,
    requested_workspace_id: str | None,
) -> None:
    try:
        await _check_workspace_supervisor(
            current_user,
            rbac,
            db,
            "task_approval",
            "create",
            project.workspace_id,
            requested_workspace_id,
        )
        return
    except ForbiddenError:
        pass

    project_member_role = await db.scalar(
        select(ProjectMember.role).where(
            ProjectMember.project_id == project.id,
            ProjectMember.user_id == current_user.id,
            ProjectMember.is_active.is_(True),
        )
    )
    if project_member_role != "manager" and project.manager_id != current_user.id:
        raise ForbiddenError("Only project managers can review submissions")


async def _check_task_assignment_access(
    current_user: CurrentUser,
    rbac: RBACAppService,
    db: AsyncSession,
    project: Project,
    task_workspace_id: str,
    assignee_id: str,
    requested_workspace_id: str | None,
) -> None:
    try:
        await _check_workspace_supervisor(
            current_user,
            rbac,
            db,
            "task",
            "update",
            task_workspace_id,
            requested_workspace_id,
        )
        await _check_workspace_supervisor(
            current_user,
            rbac,
            db,
            "task_assignment",
            "create",
            task_workspace_id,
            requested_workspace_id,
        )
        return
    except ForbiddenError:
        pass

    project_manager = project.manager_id == current_user.id or await db.scalar(
        select(ProjectMember.id).where(
            ProjectMember.project_id == project.id,
            ProjectMember.user_id == current_user.id,
            ProjectMember.role == "manager",
            ProjectMember.is_active.is_(True),
        )
    )
    if project_manager:
        return

    if assignee_id != current_user.id:
        raise ForbiddenError("Only supervisors can assign tasks to other users")
    project_member = await db.scalar(
        select(ProjectMember.id).where(
            ProjectMember.project_id == project.id,
            ProjectMember.user_id == current_user.id,
            ProjectMember.is_active.is_(True),
        )
    )
    if not project_member:
        raise ForbiddenError("You can only assign yourself to a project task")


@router.get("/projects/{project_id}/member-candidates")
async def list_project_member_candidates(
    project_id: str,
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
    workspace_id: str | None = Header(None, alias="X-Workspace-ID"),
):
    project = await db.get(Project, project_id)
    if not project or not project.workspace_id:
        raise ForbiddenError("Project is unavailable in this workspace")
    await _check_project_membership_manager(
        current_user, db, project, workspace_id
    )

    rows = (
        await db.execute(
            select(User, WorkspaceMembership, Workspace)
            .outerjoin(
                WorkspaceMembership,
                (WorkspaceMembership.user_id == User.id)
                & (WorkspaceMembership.membership_role == "supervisor")
                & (WorkspaceMembership.is_active.is_(True)),
            )
            .outerjoin(
                Workspace,
                (Workspace.id == WorkspaceMembership.workspace_id)
                & (Workspace.is_active.is_(True)),
            )
            .where(User.is_active.is_(True))
            .order_by(User.full_name, User.email, Workspace.name)
        )
    ).all()

    users: dict[str, dict[str, Any]] = {}
    for user, membership, workspace in rows:
        candidate = users.setdefault(
            user.id,
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name or user.username,
                "is_active": user.is_active,
                "memberships": [],
            },
        )
        if membership and workspace:
            candidate["memberships"].append(
                {
                    "workspace_id": workspace.id,
                    "workspace_name": workspace.name,
                    "membership_role": membership.membership_role,
                    "is_home": membership.is_home,
                }
            )

    return ActionResponse(
        status="success",
        message="Project member candidates retrieved",
        data=list(users.values()),
    )


@router.get("/my-tasks")
async def list_my_tasks(
    status: str = Query("active", pattern="^(active|completed)$"),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the signed-in user's assigned task page."""
    active_states = {
        "pending",
        "draft",
        "draft_assigned",
        "in_progress",
        "submitted",
        "for_review",
        "needs_revision",
    }
    completed_states = {"approved", "closed", "cancelled"}
    query = (
        select(Task)
        .join(TaskAssignment, TaskAssignment.task_id == Task.id)
        .where(
            TaskAssignment.user_id == current_user.id,
            TaskAssignment.is_active.is_(True),
            Task.status.in_(active_states if status == "active" else completed_states),
        )
        .distinct()
    )
    if search:
        query = query.where(Task.title.ilike(f"%{search.strip()}%"))

    total = await db.scalar(
        select(func.count()).select_from(query.order_by(None).subquery())
    )
    rows = (
        await db.scalars(
            query.order_by(Task.updated_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    return {
        "status": "success",
        "data": [record_to_dict(task) for task in rows],
        "total": total or 0,
        "page": page,
        "page_size": page_size,
    }


@router.post("/tasks")
async def create_task(
    payload: CreateTaskRequest,
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
    rbac: RBACAppService = Depends(get_rbac_service),
    workspace_id: str | None = Header(None, alias="X-Workspace-ID"),
):
    project = await db.get(Project, payload.project_id)
    if not project:
        raise ForbiddenError("Project is unavailable in this workspace")
    await _check_task_creator(
        current_user,
        db,
        project,
        workspace_id,
    )

    data = payload.model_dump(exclude_unset=True)
    if data.get("workspace_id") not in (None, project.workspace_id):
        raise ForbiddenError("Task workspace is derived from its project")
    data["workspace_id"] = project.workspace_id
    record = await ProjectTaskService.create_task(db, current_user, data)
    return ActionResponse(
        status="success",
        message="Task created",
        data=record_to_dict(record),
    )


@router.post("/tasks/{task_id}/assign")
async def assign_task(
    task_id: str,
    payload: AssignTaskRequest,
    background_tasks: BackgroundTasks,
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
    rbac: RBACAppService = Depends(get_rbac_service),
    workspace_id: str | None = Header(None, alias="X-Workspace-ID"),
):
    task = await db.get(Task, task_id)
    if not task:
        raise ForbiddenError("Task is unavailable in this workspace")
    project = await db.get(Project, task.project_id)
    task_type = await db.get(TaskType, task.task_type_id)
    if (
        not project
        or task.workspace_id != project.workspace_id
        or not task_type
        or task_type.workspace_id != project.workspace_id
    ):
        raise ForbiddenError("Project is unavailable in this workspace")
    await _check_task_assignment_access(
        current_user,
        rbac,
        db,
        project,
        project.workspace_id,
        payload.user_id,
        workspace_id,
    )

    record = await ProjectTaskService.assign_task(db, current_user, task_id, payload.user_id)
    background_tasks.add_task(
        send_task_assignment_email, task_id, record.user_id
    )
    return ActionResponse(
        status="success",
        message="Task assigned",
        data=record_to_dict(record),
    )


@router.get("/tasks/{task_id}/assignments")
async def list_task_assignments(
    task_id: str,
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
    rbac: RBACAppService = Depends(get_rbac_service),
    row_scope_service: RowScopeService = Depends(get_row_scope_service),
    page: int = 1,
    page_size: int = 50,
):
    task = await db.get(Task, task_id)
    if not task:
        raise ForbiddenError("You don't have permission to view this task")
    project = await db.get(Project, task.project_id)
    if not project:
        raise ForbiddenError("You don't have permission to view this task")
    has_permission = await rbac.check_permission(
        user_id=current_user.id,
        entity="task",
        action="read",
        role_ids=current_user.role_ids,
        is_superuser=current_user.is_superuser,
    )
    if (
        not has_permission
        and not await row_scope_service.can_read_entity(
            "task",
            current_user.id,
            current_user.roles,
            current_user.is_superuser,
        )
    ) or not await row_scope_service.can_access_record(
        task,
        "task",
        current_user.id,
        current_user.role_ids,
        current_user.roles,
        current_user.is_superuser,
    ):
        raise ForbiddenError("You don't have permission to view this task")
    membership_role = await db.scalar(
        select(WorkspaceMembership.membership_role).where(
            WorkspaceMembership.workspace_id == project.workspace_id,
            WorkspaceMembership.user_id == current_user.id,
            WorkspaceMembership.membership_role == "supervisor",
            WorkspaceMembership.is_active.is_(True),
        )
    )
    project_member_role = await db.scalar(
        select(ProjectMember.role).where(
            ProjectMember.project_id == project.id,
            ProjectMember.user_id == current_user.id,
            ProjectMember.is_active.is_(True),
        )
    )
    result = await ProjectTaskService.list_assignments(
        db,
        task_id,
        page=page,
        page_size=page_size,
        user_id=(
            None
            if WorkspaceService.is_system_admin(
                current_user.roles, current_user.is_superuser
            )
            or membership_role == "supervisor"
            or project_member_role == "manager"
            or project.manager_id == current_user.id
            else current_user.id
        ),
    )
    return ActionResponse(
        status="success",
        message="Assignments retrieved",
        data=result,
    )


async def _visible_task_ids(
    db: AsyncSession,
    row_scope_service: RowScopeService,
    current_user: CurrentUser,
    task_ids: list[str],
) -> list[str]:
    """Return the subset of task_ids the user can see under row scope."""
    if not task_ids:
        return []
    scoped = await row_scope_service.apply_scope_to_query(
        select(Task.id),
        Task,
        "task",
        current_user.id,
        current_user.role_ids,
        current_user.roles,
        current_user.is_superuser,
    )
    rows = await db.execute(scoped.where(Task.id.in_(task_ids)))
    return [row[0] for row in rows.all()]


async def _build_task_summaries(
    db: AsyncSession, task_ids: list[str]
) -> dict[str, dict[str, Any]]:
    """Return member-safe per-task summaries keyed by task id.

    Exposes only the active assignee and the current deliverable — never raw
    submission, approval, or payroll fields.
    """
    summaries: dict[str, dict[str, Any]] = {
        task_id: {
            "task_id": task_id,
            "assignee_user_id": None,
            "assignee_name": None,
            "submission_mode": "link",
            "deliverable_url": None,
            "deliverable_content": None,
            "deliverable_version": None,
            "has_deliverable": False,
        }
        for task_id in task_ids
    }
    if not task_ids:
        return summaries

    for task_id, mode in (
        await db.execute(
            select(Task.id, TaskType.submission_mode)
            .join(TaskType, Task.task_type_id == TaskType.id)
            .where(Task.id.in_(task_ids))
        )
    ).all():
        if task_id in summaries:
            summaries[task_id]["submission_mode"] = mode or "link"

    for task_id, user_id, full_name, username, email in (
        await db.execute(
            select(
                TaskAssignment.task_id,
                User.id,
                User.full_name,
                User.username,
                User.email,
            )
            .join(User, User.id == TaskAssignment.user_id)
            .where(
                TaskAssignment.task_id.in_(task_ids),
                TaskAssignment.is_active.is_(True),
            )
            .order_by(TaskAssignment.idx.desc())
        )
    ).all():
        summary = summaries.get(task_id)
        if summary and summary["assignee_user_id"] is None:
            summary["assignee_user_id"] = user_id
            summary["assignee_name"] = full_name or username or email

    # Latest submission with a deliverable wins per task.
    for task_id, link, content, version in (
        await db.execute(
            select(
                TaskAssignment.task_id,
                TaskSubmission.external_link,
                TaskSubmission.content,
                TaskSubmission.version,
            )
            .join(
                TaskAssignment,
                TaskSubmission.task_assignment_id == TaskAssignment.id,
            )
            .where(TaskAssignment.task_id.in_(task_ids))
            .order_by(
                TaskSubmission.version.desc(), TaskSubmission.submitted_at.desc()
            )
        )
    ).all():
        summary = summaries.get(task_id)
        if (
            summary
            and summary["deliverable_version"] is None
            and (link or content)
        ):
            summary["deliverable_url"] = link
            summary["deliverable_content"] = content
            summary["deliverable_version"] = version
            summary["has_deliverable"] = True

    # Fall back to the task's current link when no submission link exists.
    for task_id, url in (
        await db.execute(
            select(TaskLink.task_id, TaskLink.url)
            .where(TaskLink.task_id.in_(task_ids))
            .order_by(TaskLink.updated_at.desc())
        )
    ).all():
        summary = summaries.get(task_id)
        if summary and not summary["deliverable_url"]:
            summary["deliverable_url"] = url
            if url:
                summary["has_deliverable"] = True

    return summaries


@router.post("/tasks/summaries")
async def list_task_summaries(
    payload: TaskSummariesRequest,
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
    row_scope_service: RowScopeService = Depends(get_row_scope_service),
):
    """Batch, member-safe task summaries: active assignee + current deliverable."""
    task_ids = list(dict.fromkeys(payload.task_ids))[:200]
    visible = await _visible_task_ids(
        db, row_scope_service, current_user, task_ids
    )
    summaries = await _build_task_summaries(db, visible)
    return ActionResponse(
        status="success",
        message="Task summaries retrieved",
        data=summaries,
    )


@router.get("/tasks/{task_id}/deliverable")
async def get_task_deliverable(
    task_id: str,
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
    rbac: RBACAppService = Depends(get_rbac_service),
    row_scope_service: RowScopeService = Depends(get_row_scope_service),
):
    """Return the task's current deliverable (link or text) for any viewer."""
    task = await db.get(Task, task_id)
    if not task:
        raise ForbiddenError("You don't have permission to view this task")
    has_permission = await rbac.check_permission(
        user_id=current_user.id,
        entity="task",
        action="read",
        role_ids=current_user.role_ids,
        is_superuser=current_user.is_superuser,
    )
    if (
        not has_permission
        and not await row_scope_service.can_read_entity(
            "task",
            current_user.id,
            current_user.roles,
            current_user.is_superuser,
        )
    ) or not await row_scope_service.can_access_record(
        task,
        "task",
        current_user.id,
        current_user.role_ids,
        current_user.roles,
        current_user.is_superuser,
    ):
        raise ForbiddenError("You don't have permission to view this task")

    summaries = await _build_task_summaries(db, [task_id])
    return ActionResponse(
        status="success",
        message="Task deliverable retrieved",
        data=summaries[task_id],
    )


@router.post("/submissions")
async def create_submission(
    payload: CreateSubmissionRequest,
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
    rbac: RBACAppService = Depends(get_rbac_service),
    row_scope_service: RowScopeService = Depends(get_row_scope_service),
):
    await _check_permission(current_user, rbac, "task_submission", "create")

    data = payload.model_dump(exclude_unset=True)
    assignment = await db.get(TaskAssignment, payload.task_assignment_id)
    task = await db.get(Task, assignment.task_id) if assignment else None
    project = await db.get(Project, task.project_id) if task else None
    task_type = await db.get(TaskType, task.task_type_id) if task else None
    if (
        not project
        or not task
        or task.workspace_id != project.workspace_id
        or not task_type
        or task_type.workspace_id != project.workspace_id
    ):
        raise ForbiddenError("Task assignment is unavailable in this workspace")
    if not await row_scope_service.can_access_record(
        task,
        "task",
        current_user.id,
        current_user.role_ids,
        current_user.roles,
        current_user.is_superuser,
    ):
        raise ForbiddenError("You can only submit work for an assigned task")
    if not await db.scalar(
        select(ProjectMember.id).where(
            ProjectMember.project_id == project.id,
            ProjectMember.user_id == current_user.id,
            ProjectMember.is_active.is_(True),
        )
    ) and not WorkspaceService.is_system_admin(
        current_user.roles, current_user.is_superuser
    ):
        raise ForbiddenError("You are not a member of this project")
    record = await TaskSubmissionService.create_submission(db, current_user, data)
    return ActionResponse(
        status="success",
        message="Submission created",
        data=record_to_dict(record),
    )


@router.post("/submissions/{submission_id}/approve")
async def approve_submission(
    submission_id: str,
    payload: CreateApprovalRequest,
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
    rbac: RBACAppService = Depends(get_rbac_service),
    workspace_id: str | None = Header(None, alias="X-Workspace-ID"),
):
    submission = await db.get(TaskSubmission, submission_id)
    assignment = (
        await db.get(TaskAssignment, submission.task_assignment_id)
        if submission
        else None
    )
    task = await db.get(Task, assignment.task_id) if assignment else None
    project = await db.get(Project, task.project_id) if task else None
    task_type = await db.get(TaskType, task.task_type_id) if task else None
    if (
        not project
        or not task
        or task.workspace_id != project.workspace_id
        or not task_type
        or task_type.workspace_id != project.workspace_id
    ):
        raise ForbiddenError("Submission is unavailable in this workspace")
    await _check_submission_reviewer(
        current_user,
        rbac,
        db,
        project,
        workspace_id,
    )

    record = await TaskApprovalService.create_approval(
        db,
        current_user,
        submission_id,
        payload.decision,
        payload.remarks,
    )
    return ActionResponse(
        status="success",
        message=f"Submission {payload.decision}",
        data=record_to_dict(record),
    )
