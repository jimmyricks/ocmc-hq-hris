"""
Payroll Automation app endpoints.

Higher-level routes for payroll period management, payroll generation,
approval, and disbursement.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import uuid4

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, get_rbac_service
from app.application.services.access_control.rbac_service import RBACAppService
from app.core.exceptions import BadRequestError, ConflictError, ForbiddenError, NotFoundError
from app.core.framework.models.auth import User
from app.core.security import require_authenticated_user, CurrentUser
from app.core.serialization import record_to_dict
from app.modules.payroll.models import (
    Invoice,
    PayrollEntry,
    PayrollLineItem,
    PayrollPeriod,
    UserTaskRate,
)
from app.modules.payroll.services import PayrollService
from app.modules.collaboration_audit.services import AuditLogService
from app.modules.project_tasks.models import (
    Project,
    Task,
    TaskAssignment,
    TaskSubmission,
    TaskType,
)
from app.modules.workspaces.models import Workspace, WorkspaceMembership
from app.modules.workspaces.services import WorkspaceService
from app.schemas.base import ActionResponse

router = APIRouter(prefix="/payroll", tags=["payroll"])


class CreatePayrollPeriodRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    label: str | None = None
    period_type: str = "bi_monthly"
    start_date: date
    end_date: date
    cutoff: date | None = None


class GeneratePayrollRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    payroll_period_id: str


class EmployeeRateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace_id: str
    task_type_id: str
    user_id: str
    rate: Decimal = Field(gt=0, max_digits=12, decimal_places=2)


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


def _require_payroll_admin(current_user: CurrentUser) -> None:
    if not WorkspaceService.is_payroll_admin(
        current_user.roles, current_user.is_superuser
    ):
        raise ForbiddenError("Only HR or system administrators can manage payroll rates")


async def _validate_employee_rate(db: AsyncSession, payload: EmployeeRateRequest) -> None:
    workspace = await db.get(Workspace, payload.workspace_id)
    if not workspace or not workspace.is_active:
        raise NotFoundError("Workspace", payload.workspace_id)
    task_type = await db.get(TaskType, payload.task_type_id)
    if not task_type:
        raise NotFoundError("Task Type", payload.task_type_id)
    if task_type.workspace_id != workspace.id:
        raise BadRequestError("Task type must belong to the selected workspace")
    user = await db.get(User, payload.user_id)
    if not user or not user.is_active:
        raise NotFoundError("Active User", payload.user_id)
    member = await db.scalar(
        select(WorkspaceMembership.id).where(
            WorkspaceMembership.workspace_id == workspace.id,
            WorkspaceMembership.user_id == user.id,
            WorkspaceMembership.is_active.is_(True),
        )
    )
    if not member:
        raise BadRequestError("Employee must have an active membership in this workspace")


@router.get("/task-types")
async def list_payroll_task_types(
    search: str | None = Query(None),
    workspace_id: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
):
    """List task-rate records for payroll administrators."""
    _require_payroll_admin(current_user)
    query = select(TaskType).outerjoin(Workspace, Workspace.id == TaskType.workspace_id)
    if workspace_id:
        query = query.where(TaskType.workspace_id == workspace_id)
    if search:
        pattern = f"%{search.strip()}%"
        query = query.where(
            TaskType.name.ilike(pattern)
            | TaskType.description.ilike(pattern)
            | Workspace.name.ilike(pattern)
        )
    total = await db.scalar(
        select(func.count()).select_from(query.order_by(None).subquery())
    )
    rows = (
        await db.scalars(
            query.order_by(Workspace.name, TaskType.name)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    return {
        "status": "success",
        "data": [record_to_dict(row) for row in rows],
        "total": total or 0,
        "page": page,
        "page_size": page_size,
    }


@router.get("/rates")
async def list_employee_rates(
    workspace_id: str | None = None,
    user_id: str | None = None,
    task_type_id: str | None = None,
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
):
    _require_payroll_admin(current_user)
    query = (
        select(UserTaskRate)
        .outerjoin(User, User.id == UserTaskRate.user_id)
        .outerjoin(Workspace, Workspace.id == UserTaskRate.workspace_id)
        .outerjoin(TaskType, TaskType.id == UserTaskRate.task_type_id)
    )
    if workspace_id:
        query = query.where(UserTaskRate.workspace_id == workspace_id)
    if user_id:
        query = query.where(UserTaskRate.user_id == user_id)
    if task_type_id:
        query = query.where(UserTaskRate.task_type_id == task_type_id)
    if search:
        pattern = f"%{search.strip()}%"
        query = query.where(
            User.full_name.ilike(pattern)
            | User.email.ilike(pattern)
            | Workspace.name.ilike(pattern)
            | TaskType.name.ilike(pattern)
        )

    total = await db.scalar(
        select(func.count()).select_from(query.order_by(None).subquery())
    )
    rows = (
        await db.scalars(
            query.order_by(
                Workspace.name,
                User.full_name,
                TaskType.name,
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    return {
        "status": "success",
        "data": [record_to_dict(row) for row in rows],
        "total": total or 0,
        "page": page,
        "page_size": page_size,
    }


@router.get("/rate-options")
async def employee_rate_options(
    workspace_id: str | None = None,
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
):
    _require_payroll_admin(current_user)
    workspaces_query = select(Workspace).where(Workspace.is_active.is_(True))
    memberships_query = select(WorkspaceMembership).where(
        WorkspaceMembership.is_active.is_(True)
    )
    task_types_query = select(TaskType)
    if workspace_id:
        workspaces_query = workspaces_query.where(Workspace.id == workspace_id)
        memberships_query = memberships_query.where(
            WorkspaceMembership.workspace_id == workspace_id
        )
        task_types_query = task_types_query.where(TaskType.workspace_id == workspace_id)
    workspaces = (await db.scalars(workspaces_query.order_by(Workspace.name))).all()
    memberships = (await db.scalars(memberships_query)).all()
    user_ids = {membership.user_id for membership in memberships}
    users = (
        (
            await db.scalars(
                select(User)
                .where(User.id.in_(user_ids), User.is_active.is_(True))
                .order_by(User.full_name)
            )
        ).all()
        if user_ids
        else []
    )
    task_types = (
        await db.scalars(task_types_query.order_by(TaskType.name))
    ).all()
    return {
        "status": "success",
        "data": {
            "workspaces": [
                {"id": item.id, "name": item.name} for item in workspaces
            ],
            "users": [
                {
                    "id": item.id,
                    "full_name": item.full_name,
                    "email": item.email,
                    "workspace_ids": sorted(
                        membership.workspace_id
                        for membership in memberships
                        if membership.user_id == item.id
                    ),
                }
                for item in users
            ],
            "task_types": [
                {
                    "id": item.id,
                    "workspace_id": item.workspace_id,
                    "name": item.name,
                    "unit_rate": item.unit_rate,
                    "unit": item.unit,
                }
                for item in task_types
            ],
        },
    }


@router.post("/rates")
async def create_employee_rate(
    payload: EmployeeRateRequest,
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
):
    _require_payroll_admin(current_user)
    await _validate_employee_rate(db, payload)
    duplicate = await db.scalar(
        select(UserTaskRate.id).where(
            UserTaskRate.workspace_id == payload.workspace_id,
            UserTaskRate.task_type_id == payload.task_type_id,
            UserTaskRate.user_id == payload.user_id,
        )
    )
    if duplicate:
        raise ConflictError("An employee rate already exists for this workspace and task type")
    rate = UserTaskRate(
        id=str(uuid4()),
        workspace_id=payload.workspace_id,
        task_type_id=payload.task_type_id,
        user_id=payload.user_id,
        rate=payload.rate,
        created_by=current_user.id,
        last_modified_by=current_user.id,
    )
    db.add(rate)
    await db.flush()
    await AuditLogService.log_event(
        db,
        entity="user_task_rate",
        record_id=rate.id,
        action="create",
        actor_id=current_user.id,
        old_values=None,
        new_values=record_to_dict(rate),
    )
    await db.commit()
    await db.refresh(rate)
    return {"status": "success", "data": record_to_dict(rate)}


@router.put("/rates/{rate_id}")
async def update_employee_rate(
    rate_id: str,
    payload: EmployeeRateRequest,
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
):
    _require_payroll_admin(current_user)
    rate = await db.get(UserTaskRate, rate_id)
    if not rate:
        raise NotFoundError("Employee Rate", rate_id)
    old_values = record_to_dict(rate)
    await _validate_employee_rate(db, payload)
    duplicate = await db.scalar(
        select(UserTaskRate.id).where(
            UserTaskRate.id != rate.id,
            UserTaskRate.workspace_id == payload.workspace_id,
            UserTaskRate.task_type_id == payload.task_type_id,
            UserTaskRate.user_id == payload.user_id,
        )
    )
    if duplicate:
        raise ConflictError("An employee rate already exists for this workspace and task type")
    rate.workspace_id = payload.workspace_id
    rate.task_type_id = payload.task_type_id
    rate.user_id = payload.user_id
    rate.rate = payload.rate
    rate.last_modified_by = current_user.id
    await AuditLogService.log_event(
        db,
        entity="user_task_rate",
        record_id=rate.id,
        action="update",
        actor_id=current_user.id,
        old_values=old_values,
        new_values=record_to_dict(rate),
    )
    await db.commit()
    await db.refresh(rate)
    return {"status": "success", "data": record_to_dict(rate)}


@router.delete("/rates/{rate_id}")
async def delete_employee_rate(
    rate_id: str,
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
):
    _require_payroll_admin(current_user)
    rate = await db.get(UserTaskRate, rate_id)
    if not rate:
        raise NotFoundError("Employee Rate", rate_id)
    old_values = record_to_dict(rate)
    await db.delete(rate)
    await AuditLogService.log_event(
        db,
        entity="user_task_rate",
        record_id=rate_id,
        action="delete",
        actor_id=current_user.id,
        old_values=old_values,
        new_values=None,
    )
    await db.commit()
    return {"status": "success", "data": {"id": rate_id}}


@router.get("/hr/summary")
async def get_hr_payroll_summary(
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
):
    _require_payroll_admin(current_user)
    period_count = await db.scalar(select(func.count()).select_from(PayrollPeriod))
    entry_count = await db.scalar(select(func.count()).select_from(PayrollEntry))
    payroll_total = await db.scalar(
        select(func.coalesce(func.sum(PayrollEntry.total_amount), 0))
    )
    approved_count = await db.scalar(
        select(func.count())
        .select_from(TaskSubmission)
        .where(TaskSubmission.status == "approved")
    )
    invoice_total = await db.scalar(
        select(func.coalesce(func.sum(Invoice.total_amount), 0))
    )
    return {
        "status": "success",
        "data": {
            "period_count": period_count or 0,
            "entry_count": entry_count or 0,
            "approved_submission_count": approved_count or 0,
            "payroll_total": payroll_total,
            "invoice_total": invoice_total,
        },
    }


@router.get("/hr/tasks")
async def list_hr_payroll_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
):
    _require_payroll_admin(current_user)
    query = (
        select(TaskSubmission, TaskAssignment, Task, Project, TaskType, User)
        .join(TaskAssignment, TaskAssignment.id == TaskSubmission.task_assignment_id)
        .join(Task, Task.id == TaskAssignment.task_id)
        .join(Project, Project.id == Task.project_id)
        .outerjoin(TaskType, TaskType.id == Task.task_type_id)
        .join(User, User.id == TaskAssignment.user_id)
        .order_by(TaskSubmission.submitted_at.desc())
    )
    total = await db.scalar(
        select(func.count()).select_from(query.order_by(None).subquery())
    )
    rows = (
        await db.execute(query.offset((page - 1) * page_size).limit(page_size))
    ).all()
    return {
        "status": "success",
        "data": [
            {
                "submission_id": submission.id,
                "status": submission.status,
                "submitted_at": submission.submitted_at,
                "employee_id": employee.id,
                "employee_name": employee.full_name,
                "workspace_id": project.workspace_id,
                "project_name": project.name,
                "task_title": task.title,
                "task_type_id": task_type.id if task_type else None,
                "task_type_name": task_type.name if task_type else None,
                "approved_rate": submission.approved_rate,
                "approved_quantity": submission.approved_quantity,
                "approved_amount": submission.approved_amount,
            }
            for submission, assignment, task, project, task_type, employee in rows
        ],
        "total": total or 0,
        "page": page,
        "page_size": page_size,
    }


@router.get("/hr/users/{user_id}/rates")
async def get_employee_rate_breakdown(
    user_id: str,
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
):
    _require_payroll_admin(current_user)
    employee = await db.get(User, user_id)
    if not employee:
        raise NotFoundError("User", user_id)
    membership_workspaces = (
        select(WorkspaceMembership.workspace_id)
        .join(Workspace, Workspace.id == WorkspaceMembership.workspace_id)
        .where(
            WorkspaceMembership.user_id == user_id,
            WorkspaceMembership.is_active.is_(True),
            Workspace.is_active.is_(True),
        )
    )
    rate_rows = (
        await db.execute(
            select(TaskType, UserTaskRate)
            .outerjoin(
                UserTaskRate,
                and_(
                    UserTaskRate.task_type_id == TaskType.id,
                    UserTaskRate.workspace_id == TaskType.workspace_id,
                    UserTaskRate.user_id == user_id,
                ),
            )
            .where(TaskType.workspace_id.in_(membership_workspaces))
            .order_by(TaskType.workspace_id, TaskType.name)
        )
    ).all()
    return {
        "status": "success",
        "data": {
            "user": {"id": employee.id, "full_name": employee.full_name},
            "rates": [
                {
                    "workspace_id": task_type.workspace_id,
                    "task_type_id": task_type.id,
                    "task_type_name": task_type.name,
                    "unit": task_type.unit,
                    "default_rate": task_type.unit_rate,
                    "override_rate": override.rate if override else None,
                    "applied_rate": (
                        override.rate if override else task_type.unit_rate
                    ),
                }
                for task_type, override in rate_rows
            ],
        },
    }


@router.post("/periods")
async def create_payroll_period(
    payload: CreatePayrollPeriodRequest,
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
    rbac: RBACAppService = Depends(get_rbac_service),
):
    await _check_permission(current_user, rbac, "payroll_period", "create")

    data = payload.model_dump(exclude_unset=True)
    record = await PayrollService.create_payroll_period(db, current_user, data)
    return ActionResponse(
        status="success",
        message="Payroll period created",
        data=record_to_dict(record),
    )


@router.get("/periods/{period_id}")
async def get_payroll_period(
    period_id: str,
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
):
    _require_payroll_admin(current_user)
    period = await db.get(PayrollPeriod, period_id)
    if not period:
        raise NotFoundError("Payroll Period", period_id)
    return {"status": "success", "data": record_to_dict(period)}


@router.get("/periods/{period_id}/entries")
async def list_payroll_period_entries(
    period_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
):
    _require_payroll_admin(current_user)
    if not await db.get(PayrollPeriod, period_id):
        raise NotFoundError("Payroll Period", period_id)
    query = select(PayrollEntry).where(
        PayrollEntry.payroll_period_id == period_id
    )
    total = await db.scalar(
        select(func.count()).select_from(query.order_by(None).subquery())
    )
    entries = (
        await db.scalars(
            query.order_by(PayrollEntry.user_id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    return {
        "status": "success",
        "data": [record_to_dict(entry) for entry in entries],
        "total": total or 0,
        "page": page,
        "page_size": page_size,
    }


@router.get("/periods/{period_id}/entries/{entry_id}")
async def get_payroll_period_entry(
    period_id: str,
    entry_id: str,
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
):
    _require_payroll_admin(current_user)
    entry = await db.get(PayrollEntry, entry_id)
    if not entry or entry.payroll_period_id != period_id:
        raise NotFoundError("Payroll Entry", entry_id)
    return {"status": "success", "data": record_to_dict(entry)}


@router.post("/periods/generate")
async def generate_payroll(
    payload: GeneratePayrollRequest,
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
    rbac: RBACAppService = Depends(get_rbac_service),
):
    await _check_permission(current_user, rbac, "payroll_entry", "create")

    records = await PayrollService.generate_payroll(db, current_user, payload.payroll_period_id)
    return ActionResponse(
        status="success",
        message=f"Generated {len(records)} payroll entries",
        data={"count": len(records), "entries": [record_to_dict(r) for r in records]},
    )


@router.get("/my-invoices")
async def list_my_payroll_invoices(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(Invoice, PayrollPeriod)
        .outerjoin(PayrollPeriod, PayrollPeriod.id == Invoice.payroll_period_id)
        .where(
            Invoice.user_id == current_user.id,
            Invoice.status.in_(["issued", "paid"]),
        )
    )
    total = await db.scalar(
        select(func.count())
        .select_from(Invoice)
        .where(
            Invoice.user_id == current_user.id,
            Invoice.status.in_(["issued", "paid"]),
        )
    )
    rows = (
        await db.execute(
            query.order_by(Invoice.issued_at.desc(), Invoice.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    entry_ids = [invoice.payroll_entry_id for invoice, _ in rows]
    line_items_by_entry: dict[str, list[dict]] = {entry_id: [] for entry_id in entry_ids}
    if entry_ids:
        line_rows = (
            await db.execute(
                select(
                    PayrollLineItem,
                    Task.title,
                    TaskType.name,
                    TaskSubmission.notes,
                )
                .join(
                    TaskSubmission,
                    TaskSubmission.id == PayrollLineItem.task_submission_id,
                )
                .join(
                    TaskAssignment,
                    TaskAssignment.id == TaskSubmission.task_assignment_id,
                )
                .join(Task, Task.id == TaskAssignment.task_id)
                .outerjoin(TaskType, TaskType.id == Task.task_type_id)
                .where(PayrollLineItem.payroll_entry_id.in_(entry_ids))
                .order_by(PayrollLineItem.payroll_entry_id, PayrollLineItem.idx)
            )
        ).all()
        for line, task_title, task_type_name, notes in line_rows:
            line_items_by_entry[line.payroll_entry_id].append(
                {
                    **record_to_dict(line),
                    "task_title": task_title,
                    "task_type_name": task_type_name,
                    "submission_notes": notes,
                }
            )

    return {
        "status": "success",
        "data": [
            {
                **record_to_dict(invoice),
                "period_label": period.label if period else invoice.payroll_period_id,
                "period_start_date": period.start_date if period else None,
                "period_end_date": period.end_date if period else None,
                "line_items": line_items_by_entry.get(invoice.payroll_entry_id, []),
            }
            for invoice, period in rows
        ],
        "total": total or 0,
        "page": page,
        "page_size": page_size,
    }


@router.post("/entries/{payroll_entry_id}/approve")
async def approve_payroll_entry(
    payroll_entry_id: str,
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
    rbac: RBACAppService = Depends(get_rbac_service),
):
    await _check_permission(current_user, rbac, "payroll_entry", "update")

    record = await PayrollService.approve_payroll_entry(db, current_user, payroll_entry_id)
    return ActionResponse(
        status="success",
        message="Payroll entry approved",
        data=record_to_dict(record),
    )


@router.post("/entries/{payroll_entry_id}/pay")
async def pay_payroll_entry(
    payroll_entry_id: str,
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
    rbac: RBACAppService = Depends(get_rbac_service),
):
    await _check_permission(current_user, rbac, "payroll_entry", "update")

    record = await PayrollService.pay_payroll_entry(db, current_user, payroll_entry_id)
    return ActionResponse(
        status="success",
        message="Payroll entry paid",
        data=record_to_dict(record),
    )
