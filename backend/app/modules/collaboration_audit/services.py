"""
Collaboration & Audit domain services.

Provides application helpers for writing immutable audit logs and in-app
notifications consumed by the project-task modules and the generic CRUD layer.
"""
from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.repositories.naming_repository import NamingRepository
from app.modules.collaboration_audit.models import (
    Ledger,
    Notification,
    OcAuditLog,
)


class AuditLogService:
    """Write immutable domain audit-log rows (oc_audit_log)."""

    @staticmethod
    async def log_event(
        db: AsyncSession,
        entity: str,
        record_id: str,
        action: str,
        actor_id: str,
        old_values: Any | None = None,
        new_values: Any | None = None,
        ip_address: str | None = None,
    ) -> OcAuditLog:
        """Persist a single OcAuditLog entry.  The caller must commit."""
        naming_repo = NamingRepository(db)
        audit_id = await naming_repo.get_next_id("AUD", 5)
        audit = OcAuditLog(
            id=audit_id,
            reference_entity=entity,
            reference_id=str(record_id) if record_id is not None else None,
            action=action,
            old_values=json.dumps(old_values, default=str) if old_values is not None else None,
            new_values=json.dumps(new_values, default=str) if new_values is not None else None,
            actor_id=actor_id,
            ip_address=ip_address,
            timestamp=datetime.utcnow(),
            created_by=actor_id,
            last_modified_by=actor_id,
        )
        db.add(audit)
        await db.flush()
        return audit


class NotificationService:
    """Create in-app notifications (notification table)."""

    @staticmethod
    async def create_notification(
        db: AsyncSession,
        user_id: str,
        reference_entity: str,
        reference_id: str,
        type: str,
        message: str,
        actor_id: str,
    ) -> Notification:
        """Persist a notification row.  The caller must commit."""
        naming_repo = NamingRepository(db)
        notification_id = await naming_repo.get_next_id("NOT", 5)
        notification = Notification(
            id=notification_id,
            user_id=user_id,
            reference_entity=reference_entity,
            reference_id=reference_id,
            type=type,
            message=message,
            is_read=False,
            created_by=actor_id,
            last_modified_by=actor_id,
        )
        db.add(notification)
        await db.flush()
        return notification


class LedgerService:
    """Helpers for writing, querying, and summarizing ledger rows."""

    @staticmethod
    async def create_ledger_entry(
        db: AsyncSession,
        *,
        reference_entity: str,
        reference_id: str,
        user_id: str,
        amount: float,
        entry_type: str,
        description: str,
        period: date,
        created_by: str,
    ) -> Ledger:
        """Persist a single immutable ledger entry.  The caller must commit."""
        naming_repo = NamingRepository(db)
        ledger_id = await naming_repo.get_next_id("LED", 5)
        entry = Ledger(
            id=ledger_id,
            reference_entity=reference_entity,
            reference_id=str(reference_id) if reference_id is not None else None,
            user_id=user_id,
            amount=amount,
            entry_type=entry_type,
            description=description,
            period=period,
            created_by=created_by,
            last_modified_by=created_by,
        )
        db.add(entry)
        await db.flush()
        return entry

    @staticmethod
    def _to_float(value: Any) -> float:
        return float(value) if value is not None else 0.0

    @staticmethod
    def summary(rows: list[Ledger]) -> dict[str, Any]:
        """Return numeric totals and a per-entry_type breakdown."""
        total = sum(float(row.amount) for row in rows if row.amount is not None)
        by_type: dict[str, float] = {}
        by_user: dict[str, float] = {}
        for row in rows:
            amount = float(row.amount) if row.amount is not None else 0.0
            by_type[row.entry_type] = by_type.get(row.entry_type, 0.0) + amount
            if row.user_id:
                by_user[row.user_id] = by_user.get(row.user_id, 0.0) + amount
        return {
            "total": total,
            "count": len(rows),
            "by_entry_type": by_type,
            "by_user": by_user,
        }
