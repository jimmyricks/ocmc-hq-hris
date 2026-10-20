"""
Audit & Ledger reporting endpoints.

Provides read-only, filtered queries and summary reports for the domain
oc_audit_log and ledger tables.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, get_rbac_service
from app.application.services.access_control.rbac_service import RBACAppService
from app.core.exceptions import ForbiddenError
from app.core.security import require_authenticated_user, CurrentUser
from app.core.serialization import record_to_dict
from app.infrastructure.database.repositories.entity_repository import get_entity_model
from app.schemas.base import ActionResponse

router = APIRouter(prefix="/audit-ledger", tags=["audit-ledger"])


def _parse_json_values(row_dict: dict[str, Any]) -> dict[str, Any]:
    import json
    for key in ("old_values", "new_values"):
        if row_dict.get(key) and isinstance(row_dict[key], str):
            try:
                row_dict[key] = json.loads(row_dict[key])
            except Exception:
                pass
    return row_dict


async def _check_read_permission(
    current_user: CurrentUser,
    rbac: RBACAppService,
    entity: str,
) -> None:
    allowed = await rbac.check_permission(
        user_id=current_user.id,
        entity=entity,
        action="read",
        role_ids=current_user.role_ids,
        is_superuser=current_user.is_superuser,
    )
    if not allowed:
        raise ForbiddenError(f"You don't have permission to read {entity}")


@router.get("/audit-logs")
async def list_audit_logs(
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
    rbac: RBACAppService = Depends(get_rbac_service),
    reference_entity: str | None = Query(None),
    reference_id: str | None = Query(None),
    action: str | None = Query(None),
    actor_id: str | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    await _check_read_permission(current_user, rbac, "oc_audit_log")

    model = get_entity_model("oc_audit_log")
    q = select(model)
    if reference_entity:
        q = q.where(model.reference_entity == reference_entity)
    if reference_id:
        q = q.where(model.reference_id == reference_id)
    if action:
        q = q.where(model.action == action)
    if actor_id:
        q = q.where(model.actor_id == actor_id)
    if date_from:
        q = q.where(model.timestamp >= datetime.combine(date_from, time.min))
    if date_to:
        q = q.where(model.timestamp <= datetime.combine(date_to, time.max))

    q = q.order_by(desc(model.timestamp))
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar()
    records = (
        await db.execute(q.offset((page - 1) * page_size).limit(page_size))
    ).scalars().all()

    return ActionResponse(
        status="success",
        message="Audit logs retrieved",
        data={
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [_parse_json_values(record_to_dict(r)) for r in records],
        },
    )


@router.get("/audit-logs/report")
async def audit_log_report(
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
    rbac: RBACAppService = Depends(get_rbac_service),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    group_by: str | None = Query(None, pattern="^(action|actor|reference_entity)$"),
):
    await _check_read_permission(current_user, rbac, "oc_audit_log")

    model = get_entity_model("oc_audit_log")
    q = select(model)
    if date_from:
        q = q.where(model.timestamp >= datetime.combine(date_from, time.min))
    if date_to:
        q = q.where(model.timestamp <= datetime.combine(date_to, time.max))

    q = q.order_by(desc(model.timestamp))
    records = (await db.execute(q)).scalars().all()
    totals: dict[str, Any] = {"count": len(records)}

    if group_by == "action":
        by_action: dict[str, int] = defaultdict(int)
        for r in records:
            by_action[r.action] += 1
        totals["by_action"] = dict(by_action)
    elif group_by == "actor":
        by_actor: dict[str, int] = defaultdict(int)
        for r in records:
            by_actor[r.actor_id or "anonymous"] += 1
        totals["by_actor"] = dict(by_actor)
    elif group_by == "reference_entity":
        by_reference_entity: dict[str, int] = defaultdict(int)
        for r in records:
            by_reference_entity[r.reference_entity or "unknown"] += 1
        totals["by_reference_entity"] = dict(by_reference_entity)

    return ActionResponse(
        status="success",
        message="Audit report generated",
        data={
            "totals": totals,
            "detail": [_parse_json_values(record_to_dict(r)) for r in records],
        },
    )


@router.get("/ledger")
async def list_ledger(
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
    rbac: RBACAppService = Depends(get_rbac_service),
    user_id: str | None = Query(None),
    entry_type: str | None = Query(None),
    reference_entity: str | None = Query(None),
    period_from: date | None = Query(None),
    period_to: date | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    await _check_read_permission(current_user, rbac, "ledger")

    model = get_entity_model("ledger")
    q = select(model)
    if user_id:
        q = q.where(model.user_id == user_id)
    if entry_type:
        q = q.where(model.entry_type == entry_type)
    if reference_entity:
        q = q.where(model.reference_entity == reference_entity)
    if period_from:
        q = q.where(model.period >= period_from)
    if period_to:
        q = q.where(model.period <= period_to)

    q = q.order_by(desc(model.period), desc(model.created_at))
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar()
    records = (
        await db.execute(q.offset((page - 1) * page_size).limit(page_size))
    ).scalars().all()

    return ActionResponse(
        status="success",
        message="Ledger entries retrieved",
        data={
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [record_to_dict(r) for r in records],
        },
    )


@router.get("/ledger/report")
async def ledger_report(
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
    rbac: RBACAppService = Depends(get_rbac_service),
    user_id: str | None = Query(None),
    entry_type: str | None = Query(None),
    reference_entity: str | None = Query(None),
    period_from: date | None = Query(None),
    period_to: date | None = Query(None),
    group_by: str | None = Query(
        None, pattern="^(entry_type|user|period|reference_entity)$"
    ),
):
    await _check_read_permission(current_user, rbac, "ledger")

    model = get_entity_model("ledger")
    q = select(model)
    if user_id:
        q = q.where(model.user_id == user_id)
    if entry_type:
        q = q.where(model.entry_type == entry_type)
    if reference_entity:
        q = q.where(model.reference_entity == reference_entity)
    if period_from:
        q = q.where(model.period >= period_from)
    if period_to:
        q = q.where(model.period <= period_to)

    q = q.order_by(desc(model.period), desc(model.created_at))
    records = (await db.execute(q)).scalars().all()

    total = sum(float(r.amount) for r in records if r.amount is not None)
    totals: dict[str, Any] = {"count": len(records), "total": total}
    grouped: dict[str, float] = defaultdict(float)
    for r in records:
        amount = float(r.amount) if r.amount is not None else 0.0
        if group_by == "entry_type":
            key = r.entry_type or "unknown"
        elif group_by == "user":
            key = r.user_id or "unknown"
        elif group_by == "period":
            key = str(r.period) if r.period else "unknown"
        elif group_by == "reference_entity":
            key = r.reference_entity or "unknown"
        else:
            continue
        grouped[key] += amount
    if grouped:
        totals["grouped"] = dict(grouped)

    return ActionResponse(
        status="success",
        message="Ledger report generated",
        data={
            "totals": totals,
            "detail": [record_to_dict(r) for r in records],
        },
    )
