"""
Project & Task Management app endpoints.

Higher-level routes for task creation, assignment, and assignment listing.
Entities project and task_type are intentionally managed through the generic
entity CRUD kernel; this module exposes the task-specific workflow helpers.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, Header
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, get_rbac_service, get_row_scope_service
from app.application.services.access_control.rbac_service import RBACAppService
from app.application.services.access_control.row_scope_service import RowScopeService
from app.core.exceptions import ForbiddenError
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
from app.modules.project_tasks.models import Project, Task, TaskAssignment, TaskSubmission
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
    planned_start_at: datetime | None = None
    planned_end_at: datetime | None = None
    status: str = "pending"


class AssignTaskRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    user_id: str


class CreateSubmissionRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    task_assignment_id: str
    notes: str | None = None
    external_link: str | None = None
    previous_submission_id: str | None = None


class CreateApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    decision: str
    remarks: str | None = None


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
    await _check_workspace_supervisor(
        current_user,
        rbac,
        db,
        "task",
        "create",
        project.workspace_id,
        workspace_id,
    )

    data = payload.model_dump(exclude_unset=True)
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
    if not project:
        raise ForbiddenError("Project is unavailable in this workspace")
    await _check_workspace_supervisor(
        current_user,
        rbac,
        db,
        "task",
        "update",
        project.workspace_id,
        workspace_id,
    )
    await _check_workspace_supervisor(
        current_user,
        rbac,
        db,
        "task_assignment",
        "create",
        project.workspace_id,
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
    result = await ProjectTaskService.list_assignments(db, task_id, page=page, page_size=page_size)
    return ActionResponse(
        status="success",
        message="Assignments retrieved",
        data=result,
    )


@router.post("/submissions")
async def create_submission(
    payload: CreateSubmissionRequest,
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
    rbac: RBACAppService = Depends(get_rbac_service),
):
    await _check_permission(current_user, rbac, "task_submission", "create")

    data = payload.model_dump(exclude_unset=True)
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
    if not project:
        raise ForbiddenError("Submission is unavailable in this workspace")
    await _check_workspace_supervisor(
        current_user,
        rbac,
        db,
        "task_approval",
        "create",
        project.workspace_id,
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
