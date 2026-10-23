"""
Payroll Automation domain services.

Provides application helpers for creating payroll periods, generating payroll
entries from approved task submissions, and recording disbursement.
"""
from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any
from uuid import uuid4

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.documents.naming_service import NamingAppService
from app.application.services.entity_service import EntityService
from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.core.constants import OFFICIAL_CURRENCY
from app.core.framework.models.infrastructure import WorkflowLedger
from app.core.serialization import record_to_dict
from app.infrastructure.database.repositories.entity_repository import EntityRepository, get_entity_model
from app.infrastructure.database.repositories.naming_repository import NamingRepository
from app.meta.registry import MetaRegistry
from app.modules.collaboration_audit.services import AuditLogService, LedgerService, NotificationService
from app.modules.payroll.models import (
    Invoice,
    PayrollEntry,
    PayrollLineItem,
    PayrollPeriod,
    UserTaskRate,
)
from app.modules.project_tasks.models import (
    Project,
    Task,
    TaskAssignment,
    TaskSubmission,
    TaskType,
)


def _id_or_uuid(generated_id: str | None) -> str:
    """Return the generated naming id, or a UUID when naming is disabled."""
    return generated_id or str(uuid4())


_CENT = Decimal("0.01")


def _money(value: Any) -> Decimal:
    try:
        amount = Decimal(str(value))
        if not amount.is_finite():
            raise InvalidOperation
        return amount.quantize(_CENT, rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError, ValueError):
        raise BadRequestError("Payroll rates and amounts must be valid decimals")


class PayrollService:
    """Application helpers for payroll period generation and disbursement."""

    @staticmethod
    async def create_payroll_period(
        db: AsyncSession, user: Any, data: dict[str, Any]
    ) -> PayrollPeriod:
        """Create a payroll period after validating the date range.

        Periods are the 1st–14th and 15th–month-end halves of one month.
        """
        start_date = data.get("start_date")
        end_date = data.get("end_date")
        cutoff = data.get("cutoff")
        period_type = data.get("period_type", "bi_monthly")

        if not start_date or not end_date:
            raise BadRequestError("start_date and end_date are required")
        if period_type != "bi_monthly":
            raise BadRequestError("Payroll periods must use the bi-monthly schedule")
        if cutoff and cutoff != end_date:
            raise BadRequestError("cutoff must match the payroll period end date")
        PayrollService._validate_period_range(start_date, end_date)
        overlap = await db.scalar(
            select(func.count())
            .select_from(PayrollPeriod)
            .where(
                PayrollPeriod.start_date <= end_date,
                PayrollPeriod.end_date >= start_date,
            )
        )
        if overlap:
            raise ConflictError("A payroll period already covers some or all of these dates")

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

        Period membership uses the recorded transition into Done. Approved
        snapshots remain authoritative; legacy work without a transition date
        or pay snapshot must be reviewed rather than assigned to a period by guess.
        """
        period = await db.scalar(
            select(PayrollPeriod)
            .where(PayrollPeriod.id == payroll_period_id)
            .with_for_update()
        )
        if not period:
            raise NotFoundError("Payroll Period", payroll_period_id)
        if period.cutoff and period.cutoff != period.end_date:
            raise BadRequestError("Payroll period cutoff must match its end date")
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
        end_exclusive = datetime.combine(
            date.fromordinal(period.end_date.toordinal() + 1),
            datetime.min.time(),
        )
        done_transitions = (
            select(
                WorkflowLedger.record_id.label("task_id"),
                func.max(WorkflowLedger.changed_at).label("done_at"),
            )
            .where(
                WorkflowLedger.entity_type == "task",
                WorkflowLedger.previous_state == "approved",
                WorkflowLedger.next_state == "done",
            )
            .group_by(WorkflowLedger.record_id)
            .subquery()
        )
        has_done_transition = select(WorkflowLedger.id).where(
            WorkflowLedger.entity_type == "task",
            WorkflowLedger.record_id == Task.id,
            WorkflowLedger.previous_state == "approved",
            WorkflowLedger.next_state == "done",
        ).exists()
        missing_done_dates = (
            await db.scalars(
                select(Task.id)
                .join(TaskAssignment, TaskAssignment.task_id == Task.id)
                .join(
                    TaskSubmission,
                    TaskSubmission.task_assignment_id == TaskAssignment.id,
                )
                .where(
                    Task.status == "done",
                    TaskSubmission.status == "approved",
                    ~has_done_transition,
                )
                .limit(5)
            )
        ).all()
        if missing_done_dates:
            raise BadRequestError(
                "Approved Done tasks without a recorded Done date need manual review: "
                + ", ".join(missing_done_dates)
            )

        submissions_result = await db.execute(
            select(
                TaskSubmission,
                TaskAssignment,
                TaskType,
                Project.workspace_id,
                done_transitions.c.done_at,
            )
            .join(
                TaskAssignment,
                TaskSubmission.task_assignment_id == TaskAssignment.id,
            )
            .join(Task, TaskAssignment.task_id == Task.id)
            .join(Project, Project.id == Task.project_id)
            .outerjoin(TaskType, Task.task_type_id == TaskType.id)
            .join(done_transitions, done_transitions.c.task_id == Task.id)
            .where(
                TaskSubmission.status == "approved",
                Task.status == "done",
                done_transitions.c.done_at >= start_dt,
                done_transitions.c.done_at < end_exclusive,
            )
            .order_by(done_transitions.c.done_at, TaskSubmission.id)
        )
        submission_rows = submissions_result.all()

        # Group snapshots by assignee. Never resolve current rates during payroll.
        by_user: dict[
            str, list[tuple[TaskSubmission, str | None, Decimal, Decimal, Decimal]]
        ] = {}
        for submission, assignment, task_type, workspace_id, _done_at in submission_rows:
            if not workspace_id or not task_type or task_type.workspace_id != workspace_id:
                raise BadRequestError(
                    "Approved work has unmapped or cross-workspace project/task-type data"
                )
            if (
                submission.approved_rate is None
                or submission.approved_quantity is None
                or submission.approved_amount is None
            ):
                raise BadRequestError(
                    f"Approved submission {submission.id} has no pay snapshot; "
                    "review its historical rate before payroll generation"
                )
            rate = _money(submission.approved_rate)
            quantity = _money(submission.approved_quantity)
            amount = _money(submission.approved_amount)
            if rate <= 0 or quantity != Decimal("1.00"):
                raise BadRequestError(
                    f"Approved submission {submission.id} has an invalid pay snapshot"
                )
            if _money(rate * quantity) != amount:
                raise BadRequestError(
                    f"Approved submission {submission.id} has an inconsistent pay snapshot"
                )
            by_user.setdefault(assignment.user_id, []).append(
                (submission, workspace_id, rate, quantity, amount)
            )

        submission_ids = {
            submission.id
            for user_submissions in by_user.values()
            for submission, *_ in user_submissions
        }
        if submission_ids:
            duplicate_ids = (
                await db.scalars(
                    select(PayrollLineItem.task_submission_id)
                    .join(
                        PayrollEntry,
                        PayrollEntry.id == PayrollLineItem.payroll_entry_id,
                    )
                    .where(
                        PayrollLineItem.task_submission_id.in_(submission_ids),
                        PayrollEntry.payroll_period_id != payroll_period_id,
                    )
                )
            ).all()
            if duplicate_ids:
                raise BadRequestError(
                    "Approved work is already included in another payroll period: "
                    + ", ".join(sorted(set(duplicate_ids)))
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
                    "total_amount": Decimal("0.00"),
                    "status": "draft",
                    "generated_at": now,
                    "created_by": user.id,
                    "last_modified_by": user.id,
                },
            )
            entry = await EntityRepository(db).create("payroll_entry", entry_data)

            total = Decimal("0.00")
            for idx, (submission, workspace_id, rate, quantity, amount) in enumerate(
                user_submissions, start=1
            ):
                total += amount

                line_id = _id_or_uuid(
                    await naming_service.generate_id(line_meta.naming, "payroll_line_item")
                )
                db.add(
                    PayrollLineItem(
                        id=line_id,
                        payroll_entry_id=entry.id,
                        idx=idx,
                        task_submission_id=submission.id,
                        workspace_id=workspace_id,
                        rate=rate,
                        quantity=quantity,
                        amount=amount,
                        created_by=user.id,
                        last_modified_by=user.id,
                    )
                )

            entry.total_amount = _money(total)
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
        entry = await db.scalar(
            select(PayrollEntry)
            .where(PayrollEntry.id == payroll_entry_id)
            .with_for_update()
        )
        if not entry:
            raise NotFoundError("Payroll Entry", payroll_entry_id)
        if entry.status not in {"draft", "under_review"}:
            raise BadRequestError("Payroll entry cannot be approved from its current status")
        period = await db.get(PayrollPeriod, entry.payroll_period_id)
        line_total = await db.scalar(
            select(func.coalesce(func.sum(PayrollLineItem.amount), 0)).where(
                PayrollLineItem.payroll_entry_id == entry.id
            )
        )
        total = _money(line_total)
        if total != _money(entry.total_amount or 0):
            raise BadRequestError(
                "Payroll entry total does not match its line items; reconcile before approval"
            )
        invoice = await PayrollService._ensure_invoice(
            db, user, entry, period, total, status="issued"
        )

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
        await NotificationService.create_notification(
            db,
            user_id=entry.user_id,
            reference_entity="invoice",
            reference_id=invoice.id,
            type="payroll_invoice_issued",
            message=(
                f"Invoice {invoice.invoice_number} for {total} is available "
                f"for {period.label if period else entry.payroll_period_id}."
            ),
            actor_id=user.id,
        )
        await db.commit()
        return entry

    @staticmethod
    async def pay_payroll_entry(
        db: AsyncSession, user: Any, payroll_entry_id: str
    ) -> PayrollEntry:
        """Mark a payroll entry as paid and record a ledger debit."""
        entry = await db.scalar(
            select(PayrollEntry)
            .where(PayrollEntry.id == payroll_entry_id)
            .with_for_update()
        )
        if not entry:
            raise NotFoundError("Payroll Entry", payroll_entry_id)
        if entry.status != "approved":
            raise BadRequestError("Payroll entry must be approved before payment")

        period = await db.get(PayrollPeriod, entry.payroll_period_id)
        line_total = await db.scalar(
            select(func.coalesce(func.sum(PayrollLineItem.amount), 0)).where(
                PayrollLineItem.payroll_entry_id == entry.id
            )
        )
        total = _money(line_total)
        if total != _money(entry.total_amount or 0):
            raise BadRequestError(
                "Payroll entry total does not match its line items; reconcile before payment"
            )

        invoice = await PayrollService._ensure_invoice(
            db, user, entry, period, total, status="issued"
        )
        if invoice.status != "issued":
            raise BadRequestError("Only an issued invoice can be paid")

        from app.modules.collaboration_audit.models import Ledger

        existing_debit = await db.scalar(
            select(Ledger.id).where(
                Ledger.reference_entity == "payroll_entry",
                Ledger.reference_id == entry.id,
                Ledger.entry_type == "debit",
            )
        )
        if not existing_debit:
            await LedgerService.create_ledger_entry(
                db,
                reference_entity="payroll_entry",
                reference_id=entry.id,
                user_id=entry.user_id,
                amount=total,
                entry_type="debit",
                description=(
                    f"Payroll disbursement for period "
                    f"{period.label if period else entry.payroll_period_id}"
                ),
                period=period.end_date if period else date.today(),
                created_by=user.id,
            )

        old_status = entry.status
        entry.status = "paid"
        entry.last_modified_by = user.id
        invoice.status = "paid"
        invoice.paid_at = datetime.utcnow()
        invoice.last_modified_by = user.id

        await AuditLogService.log_event(
            db,
            entity="invoice",
            record_id=invoice.id,
            action="update",
            actor_id=user.id,
            old_values={"status": "issued", "paid_at": None},
            new_values={"status": "paid", "paid_at": invoice.paid_at},
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
            message=(
                f"Your payroll of {total} has been disbursed for period "
                f"{period.label if period else entry.payroll_period_id}."
            ),
            actor_id=user.id,
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
    async def _ensure_invoice(
        db: AsyncSession,
        user: Any,
        entry: PayrollEntry,
        period: PayrollPeriod | None,
        total: Decimal,
        status: str,
    ) -> Invoice:
        invoice = await db.scalar(
            select(Invoice)
            .where(Invoice.payroll_entry_id == entry.id)
            .with_for_update()
        )
        if invoice:
            if (
                invoice.user_id != entry.user_id
                or invoice.payroll_period_id != entry.payroll_period_id
                or _money(invoice.total_amount or 0) != total
            ):
                raise BadRequestError(
                    "An existing invoice does not reconcile with this payroll entry"
                )
            if invoice.status != "issued":
                raise BadRequestError("Payroll invoice must be issued before approval or payment")
            return invoice

        naming_service = NamingAppService(NamingRepository(db))
        invoice_meta = MetaRegistry.get("invoice")
        invoice_id = _id_or_uuid(
            await naming_service.generate_id(invoice_meta.naming, "invoice")
        )
        label = period.label if period else entry.payroll_period_id
        invoice = Invoice(
            id=invoice_id,
            payroll_entry_id=entry.id,
            payroll_period_id=entry.payroll_period_id,
            user_id=entry.user_id,
            invoice_number=f"INV-{label.replace(' ', '-').upper()}-{entry.user_id[-6:]}",
            total_tasks=entry.total_tasks or 0,
            total_amount=total,
            currency=OFFICIAL_CURRENCY,
            status=status,
            issued_at=datetime.utcnow(),
            created_by=user.id,
            last_modified_by=user.id,
        )
        db.add(invoice)
        await db.flush()
        await AuditLogService.log_event(
            db,
            entity="invoice",
            record_id=invoice.id,
            action="create",
            actor_id=user.id,
            old_values=None,
            new_values=record_to_dict(invoice),
        )
        return invoice

    @staticmethod
    async def resolve_rate(
        db: AsyncSession,
        task_type: TaskType | None,
        workspace_id: str | None,
        user_id: str,
    ) -> Decimal:
        if not workspace_id:
            raise BadRequestError(
                "Map the project to a workspace before generating payroll"
            )
        if not task_type or task_type.workspace_id != workspace_id:
            raise BadRequestError(
                "Map the task type to the project's workspace before generating payroll"
            )
        if task_type.unit == "per_hour":
            raise BadRequestError(
                "Hourly task types require captured hours; payroll currently pays "
                "one deliverable per approved submission"
            )
        override = await db.scalar(
            select(UserTaskRate).where(
                UserTaskRate.workspace_id == workspace_id,
                UserTaskRate.task_type_id == task_type.id,
                UserTaskRate.user_id == user_id,
            )
        )
        rate = _money(override.rate if override else task_type.unit_rate)
        if rate <= 0:
            raise BadRequestError(
                "A positive employee override or workspace default rate is required"
            )
        return rate

    @staticmethod
    def resolve_snapshot(rate: Any, quantity: Any = Decimal("1.00")) -> tuple[Decimal, Decimal, Decimal]:
        """Validate and calculate the immutable unit snapshot for approved work."""
        applied_rate = _money(rate)
        applied_quantity = _money(quantity)
        if applied_rate <= 0 or applied_quantity != Decimal("1.00"):
            raise BadRequestError(
                "Payroll currently pays one approved deliverable per submission; "
                "the rate must be positive"
            )
        return applied_rate, applied_quantity, _money(applied_rate * applied_quantity)

    @staticmethod
    def bi_monthly_periods(year: int, month: int) -> tuple[dict[str, Any], dict[str, Any]]:
        """Return the 1–14 and 15–month-end periods for a month."""
        _, last_day = monthrange(year, month)
        first = {
            "start_date": date(year, month, 1),
            "end_date": date(year, month, 14),
            "cutoff": date(year, month, 14),
        }
        second = {
            "start_date": date(year, month, 15),
            "end_date": date(year, month, last_day),
            "cutoff": date(year, month, last_day),
        }
        return first, second

    @staticmethod
    def _validate_period_range(start_date: date, end_date: date) -> None:
        if start_date > end_date:
            raise BadRequestError("start_date must be on or before end_date")
        first, second = PayrollService.bi_monthly_periods(
            start_date.year, start_date.month
        )
        valid_ranges = {
            (first["start_date"], first["end_date"]),
            (second["start_date"], second["end_date"]),
        }
        if (start_date, end_date) not in valid_ranges:
            raise BadRequestError(
                "Payroll periods must cover either days 1–14 or day 15 through month-end"
            )
