"""
Payroll Automation app endpoints.

Higher-level routes for payroll period management, payroll generation,
approval, and disbursement.
"""
from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, get_rbac_service
from app.application.services.access_control.rbac_service import RBACAppService
from app.core.exceptions import ForbiddenError
from app.core.security import require_authenticated_user, CurrentUser
from app.core.serialization import record_to_dict
from app.modules.payroll.services import PayrollService
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
