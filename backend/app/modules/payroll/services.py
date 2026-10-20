"""
Payroll Automation domain services.

Provides application helpers for creating payroll periods, generating payroll
entries from approved task submissions, and recording disbursement.
"""
from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.documents.naming_service import NamingAppService
from app.application.services.entity_service import EntityService
from app.core.exceptions import BadRequestError, NotFoundError
from app.core.constants import OFFICIAL_CURRENCY
from app.core.serialization import record_to_dict
from app.infrastructure.database.repositories.entity_repository import EntityRepository, get_entity_model
from app.infrastructure.database.repositories.naming_repository import NamingRepository
from app.meta.registry import MetaRegistry
from app.modules.collaboration_audit.services import AuditLogService, LedgerService, NotificationService
from app.modules.payroll.models import PayrollEntry, PayrollLineItem, PayrollPeriod, Invoice
from app.modules.project_tasks.models import Project, Task, TaskAssignment, TaskSubmission, TaskType


def _id_or_uuid(generated_id: str | None) -> str:
    """Return the generated naming id, or a UUID when naming is disabled."""
    return generated_id or str(uuid4())


class PayrollService:
    """Application helpers for payroll period generation and disbursement."""

    @staticmethod
    async def create_payroll_period(
        db: AsyncSession, user: Any, data: dict[str, Any]
    ) -> PayrollPeriod:
        """Create a payroll period after validating the date range.

        Real-world rules:
        - ``start_date`` must be before ``end_date``.
        - ``cutoff`` must fall on or before ``end_date``.
        - The label is auto-generated when missing.
        """
        start_date = data.get("start_date")
        end_date = data.get("end_date")
        cutoff = data.get("cutoff")
        period_type = data.get("period_type", "bi_monthly")

        if not start_date or not end_date:
            raise BadRequestError("start_date and end_date are required")
        if start_date > end_date:
            raise BadRequestError("start_date must be before end_date")
        if cutoff and cutoff > end_date:
            raise BadRequestError("cutoff must be on or before end_date")

        label = data.get("label")
        if not label:
            label = f"Payroll {start_date} - {end_date}"

        meta = MetaRegistry.get("payroll_period")
        naming_service = NamingAppService(NamingRepository(db))
        period_id = _id_or_uuid(
            await naming_service.generate_id(meta.naming, "payroll_period")
        )

        model = get_entity_model("payroll_period")
        payload = EntityService.coerce_incoming_types(model, data)
        payload.update(
            {
                "id": period_id,
                "label": label,
                "period_type": period_type,
                "start_date": start_date,
                "end_date": end_date,
                "cutoff": cutoff or end_date,
                "status": "open",
                "is_auto_generated": data.get("is_auto_generated", False),
                "created_by": user.id,
                "last_modified_by": user.id,
            }
        )

        record = await EntityRepository(db).create("payroll_period", payload)
        await AuditLogService.log_event(
            db,
            entity="payroll_period",
            record_id=record.id,
            action="create",
            actor_id=user.id,
            old_values=None,
            new_values=record_to_dict(record),
        )
        await db.commit()
        await db.refresh(record)
        return record

    @staticmethod
    async def generate_payroll(
        db: AsyncSession, user: Any, payroll_period_id: str
    ) -> list[PayrollEntry]:
        """Generate payroll entries and line items for a period.

        Real-world rules:
        - Only ``approved`` submissions within the period are included.
        - Each user gets one PayrollEntry.
        - Each submission becomes a PayrollLineItem with ``amount = rate * quantity``.
        - ``PayrollEntry.total_amount`` is the sum of its line items.
        - Existing generated entries for the period are removed and recreated.
        """
        period = await db.get(PayrollPeriod, payroll_period_id)
        if not period:
            raise NotFoundError("Payroll Period", payroll_period_id)
        if period.status == "paid":
            raise BadRequestError("Cannot generate payroll for a paid period")

        has_finalized_entries = await db.scalar(
            select(func.count())
            .select_from(PayrollEntry)
            .where(
                PayrollEntry.payroll_period_id == payroll_period_id,
                PayrollEntry.status.notin_(["draft", "under_review"]),
            )
        )
        if has_finalized_entries:
            raise BadRequestError(
                "Cannot regenerate payroll after an entry has been approved or paid"
            )

        start_dt = datetime.combine(period.start_date, datetime.min.time())
        end_dt = datetime.combine(period.end_date, datetime.max.time())

        submissions_result = await db.execute(
            select(TaskSubmission, TaskAssignment, Task, TaskType, Project.workspace_id)
            .join(
                TaskAssignment,
                TaskSubmission.task_assignment_id == TaskAssignment.id,
            )
            .join(Task, TaskAssignment.task_id == Task.id)
            .join(Project, Project.id == Task.project_id)
            .outerjoin(TaskType, Task.task_type_id == TaskType.id)
            .where(
                TaskSubmission.status == "approved",
                TaskSubmission.submitted_at >= start_dt,
                TaskSubmission.submitted_at <= end_dt,
            )
            .order_by(TaskSubmission.submitted_at)
        )
        submission_rows = submissions_result.all()

        # Join assignment, task, and rate data once instead of loading each row in loops.
        by_user: dict[str, list[tuple[TaskSubmission, Task, TaskType | None, str | None]]] = {}
        for submission, assignment, task, task_type, workspace_id in submission_rows:
            PayrollService._resolve_rate(task_type, workspace_id)
            by_user.setdefault(assignment.user_id, []).append(
                (submission, task, task_type, workspace_id)
            )

        # Remove existing draft/under_review entries for this period before regenerating
        old_entries_result = await db.execute(
            select(PayrollEntry).where(
                PayrollEntry.payroll_period_id == payroll_period_id,
                PayrollEntry.status.in_(["draft", "under_review"]),
            )
        )
        old_entries = old_entries_result.scalars().all()
        if old_entries:
            old_entry_ids = [entry.id for entry in old_entries]
            await db.execute(
                delete(PayrollLineItem).where(
                    PayrollLineItem.payroll_entry_id.in_(old_entry_ids)
                )
            )
            for old_entry in old_entries:
                await db.delete(old_entry)

        created_entries: list[PayrollEntry] = []
        naming_service = NamingAppService(NamingRepository(db))
        entry_meta = MetaRegistry.get("payroll_entry")
        line_meta = MetaRegistry.get("payroll_line_item")
        entry_model = get_entity_model("payroll_entry")
        line_model = get_entity_model("payroll_line_item")
        now = datetime.utcnow()

        for user_id, user_submissions in by_user.items():
            entry_id = _id_or_uuid(
                await naming_service.generate_id(entry_meta.naming, "payroll_entry")
            )
            entry_data = EntityService.coerce_incoming_types(
                entry_model,
                {
                    "id": entry_id,
                    "payroll_period_id": payroll_period_id,
                    "user_id": user_id,
                    "total_tasks": len(user_submissions),
                    "total_amount": 0.0,
                    "status": "draft",
                    "generated_at": now,
                    "created_by": user.id,
                    "last_modified_by": user.id,
                },
            )
            entry = await EntityRepository(db).create("payroll_entry", entry_data)

            total = 0.0
            for idx, (submission, task, task_type, workspace_id) in enumerate(
                user_submissions, start=1
            ):
                rate = PayrollService._resolve_rate(task_type, workspace_id)
                quantity = 1.0
                amount = round(rate * quantity, 2)
                total += amount

                line_id = _id_or_uuid(
                    await naming_service.generate_id(line_meta.naming, "payroll_line_item")
                )
                line_data = EntityService.coerce_incoming_types(
                    line_model,
                    {
                        "id": line_id,
                        "payroll_entry_id": entry.id,
                        "idx": idx,
                        "task_submission_id": submission.id,
                        "workspace_id": workspace_id,
                        "rate": rate,
                        "quantity": quantity,
                        "amount": amount,
                        "created_by": user.id,
                        "last_modified_by": user.id,
                    },
                )
                await EntityRepository(db).create("payroll_line_item", line_data)

                # Auto-close the approved task to preserve data integrity
                if task and task.status == "approved":
                    old_task_status = task.status
                    task.status = "closed"
                    task.last_modified_by = user.id
                    await AuditLogService.log_event(
                        db,
                        entity="task",
                        record_id=task.id,
                        action="update",
                        actor_id=user.id,
                        old_values={"status": old_task_status},
                        new_values={"status": "closed", "reason": "auto-closed by payroll generation"},
                    )

            entry.total_amount = round(total, 2)
            entry.last_modified_by = user.id
            created_entries.append(entry)

            await AuditLogService.log_event(
                db,
                entity="payroll_entry",
                record_id=entry.id,
                action="create",
                actor_id=user.id,
                old_values=None,
                new_values=record_to_dict(entry),
            )

        period.status = "open"
        period.last_modified_by = user.id

        await AuditLogService.log_event(
            db,
            entity="payroll_period",
            record_id=period.id,
            action="update",
            actor_id=user.id,
            old_values=None,
            new_values={"generated_entries": len(created_entries)},
        )
        await db.commit()
        return created_entries

    @staticmethod
    async def approve_payroll_entry(
        db: AsyncSession, user: Any, payroll_entry_id: str
    ) -> PayrollEntry:
        """Move a payroll entry to approved status."""
        entry = await db.get(PayrollEntry, payroll_entry_id)
        if not entry:
            raise NotFoundError("Payroll Entry", payroll_entry_id)
        if entry.status not in {"draft", "under_review"}:
            raise BadRequestError("Payroll entry cannot be approved from its current status")

        old_status = entry.status
        entry.status = "approved"
        entry.approved_by = user.id
        entry.approved_at = datetime.utcnow()
        entry.last_modified_by = user.id

        await AuditLogService.log_event(
            db,
            entity="payroll_entry",
            record_id=entry.id,
            action="update",
            actor_id=user.id,
            old_values={"status": old_status},
            new_values={"status": entry.status, "approved_by": user.id},
        )
        await db.commit()
        return entry

    @staticmethod
    async def pay_payroll_entry(
        db: AsyncSession, user: Any, payroll_entry_id: str
    ) -> PayrollEntry:
        """Mark a payroll entry as paid and record a ledger debit."""
        entry = await db.get(PayrollEntry, payroll_entry_id)
        if not entry:
            raise NotFoundError("Payroll Entry", payroll_entry_id)
        if entry.status != "approved":
            raise BadRequestError("Payroll entry must be approved before payment")

        period = await db.get(PayrollPeriod, entry.payroll_period_id)
        old_status = entry.status
        entry.status = "paid"
        entry.last_modified_by = user.id

        naming_service = NamingAppService(NamingRepository(db))

        await LedgerService.create_ledger_entry(
            db,
            reference_entity="payroll_entry",
            reference_id=entry.id,
            user_id=entry.user_id,
            amount=float(entry.total_amount or 0),
            entry_type="debit",
            description=f"Payroll disbursement for period {period.label if period else entry.payroll_period_id}",
            period=period.end_date if period else date.today(),
            created_by=user.id,
        )

        await AuditLogService.log_event(
            db,
            entity="payroll_entry",
            record_id=entry.id,
            action="update",
            actor_id=user.id,
            old_values={"status": old_status},
            new_values={"status": "paid"},
        )

        await NotificationService.create_notification(
            db,
            user_id=entry.user_id,
            reference_entity="payroll_entry",
            reference_id=entry.id,
            type="payroll_ready",
            message=f"Your payroll of {entry.total_amount} has been disbursed for period {period.label if period else entry.payroll_period_id}.",
            actor_id=user.id,
        )

        # Generate an invoice for the paid entry
        invoice_meta = MetaRegistry.get("invoice")
        invoice_model = get_entity_model("invoice")
        invoice_id = _id_or_uuid(
            await naming_service.generate_id(invoice_meta.naming, "invoice")
        )
        invoice_number = f"INV-{period.label.replace(' ', '-').upper()}-{entry.user_id[-6:]}" if period else f"INV-{entry.id[-8:]}"
        invoice_data = EntityService.coerce_incoming_types(
            invoice_model,
            {
                "id": invoice_id,
                "payroll_entry_id": entry.id,
                "payroll_period_id": entry.payroll_period_id,
                "user_id": entry.user_id,
                "invoice_number": invoice_number,
                "total_tasks": entry.total_tasks or 0,
                "total_amount": entry.total_amount or 0,
                "currency": OFFICIAL_CURRENCY,
                "status": "paid",
                "issued_at": datetime.utcnow(),
                "paid_at": datetime.utcnow(),
                "created_by": user.id,
                "last_modified_by": user.id,
            },
        )
        invoice = await EntityRepository(db).create("invoice", invoice_data)
        await AuditLogService.log_event(
            db,
            entity="invoice",
            record_id=invoice.id,
            action="create",
            actor_id=user.id,
            old_values=None,
            new_values=record_to_dict(invoice),
        )

        if period:
            unpaid_entries = await db.scalar(
                select(func.count())
                .select_from(PayrollEntry)
                .where(
                    PayrollEntry.payroll_period_id == period.id,
                    PayrollEntry.status != "paid",
                )
            )
            period.status = "open" if unpaid_entries else "paid"
            period.last_modified_by = user.id

        await db.commit()
        await db.refresh(entry)
        return entry

    @staticmethod
    def _resolve_rate(
        task_type: TaskType | None, workspace_id: str | None
    ) -> float:
        if not workspace_id:
            raise BadRequestError(
                "Map the project to a workspace before generating payroll"
            )
        if not task_type or task_type.workspace_id != workspace_id:
            raise BadRequestError(
                "Map the task type to the project's workspace before generating payroll"
            )
        return (
            float(task_type.unit_rate)
            if task_type.unit_rate is not None
            else 0.0
        )

    @staticmethod
    def bi_monthly_periods(year: int, month: int) -> tuple[dict[str, Any], dict[str, Any]]:
        """Return the first-half and second-half bi-monthly periods for a month."""
        _, last_day = monthrange(year, month)
        first = {
            "start_date": date(year, month, 1),
            "end_date": date(year, month, 15),
            "cutoff": date(year, month, 15),
        }
        second = {
            "start_date": date(year, month, 16),
            "end_date": date(year, month, last_day),
            "cutoff": date(year, month, last_day),
        }
        return first, second
