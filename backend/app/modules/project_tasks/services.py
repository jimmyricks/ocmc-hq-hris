"""
Project & Task Management domain services.

Business helpers for creating tasks, assigning users, and emitting the
audit and notification side-effects required by the project-task story.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.documents.naming_service import NamingAppService
from app.application.services.entity_service import EntityService
from app.core.exceptions import BadRequestError, ForbiddenError, NotFoundError
from app.core.constants import DEFAULT_TASK_PRIORITY
from app.core.framework.models.auth import User
from app.core.serialization import record_to_dict
from app.infrastructure.database.repositories.entity_repository import (
    EntityRepository,
    get_entity_model,
)
from app.infrastructure.database.repositories.naming_repository import NamingRepository
from app.meta.registry import MetaRegistry
from app.modules.collaboration_audit.services import AuditLogService, LedgerService, NotificationService
from app.modules.project_tasks.models import (
    Project,
    ProjectMember,
    Task,
    TaskApproval,
    TaskAssignment,
    TaskSubmission,
    TaskType,
)


def _id_or_uuid(generated_id: str | None) -> str:
    """Return the generated naming id, or a UUID when naming is disabled."""
    return generated_id or str(uuid4())


def _task_label(task: Task) -> str:
    """Return the task key if present, otherwise the task id."""
    return getattr(task, "task_key", None) or task.id


class ProjectTaskService:
    """Application helpers for project/task/assignment operations."""

    # ------------------------------------------------------------------
    # Task lifecycle
    # ------------------------------------------------------------------
    @staticmethod
    async def finalize_task(record: Task, db: AsyncSession) -> Task:
        """Generate the human-readable task key once the record id is known."""
        if getattr(record, "task_key", None) or not hasattr(Task, "task_key"):
            return record

        project = await db.get(Project, record.project_id)
        if not project:
            return record

        naming_repo = NamingRepository(db)
        prefix = getattr(project, "code", None) or project.id
        record.task_key = await naming_repo.get_next_id(prefix, 3)
        return record

    @staticmethod
    async def create_task(db: AsyncSession, user: Any, data: dict[str, Any]) -> Task:
        """Create a task, generate its key, and write an audit log."""
        project = await db.get(Project, data.get("project_id"))
        if not project:
            raise NotFoundError("Project", data.get("project_id"))

        task_type = await db.get(TaskType, data.get("task_type_id"))
        if not task_type:
            raise NotFoundError("Task Type", data.get("task_type_id"))
        if project.workspace_id and task_type.workspace_id != project.workspace_id:
            raise BadRequestError("Task type must belong to the project's workspace")

        model = get_entity_model("task")
        data = EntityService.coerce_incoming_types(model, data)

        naming_service = NamingAppService(NamingRepository(db))
        meta = MetaRegistry.get("task")
        data["id"] = _id_or_uuid(await naming_service.generate_id(meta.naming, "task"))
        data.setdefault("status", "pending")
        data.setdefault("priority", DEFAULT_TASK_PRIORITY)
        data["created_by"] = user.id
        data["last_modified_by"] = user.id

        record = await EntityRepository(db).create("task", data)
        await ProjectTaskService.finalize_task(record, db)
        await AuditLogService.log_event(
            db,
            entity="task",
            record_id=record.id,
            action="create",
            actor_id=user.id,
            old_values=None,
            new_values=record_to_dict(record),
        )
        await db.commit()
        await db.refresh(record)
        return record

    # ------------------------------------------------------------------
    # Assignment lifecycle
    # ------------------------------------------------------------------
    @staticmethod
    async def next_assignment_index(db: AsyncSession, task_id: str) -> int:
        """Return the next available idx for a task assignment."""
        result = await db.execute(
            select(func.max(TaskAssignment.idx)).where(TaskAssignment.task_id == task_id)
        )
        max_idx = result.scalar() or 0
        return int(max_idx) + 1

    @staticmethod
    async def post_create_assignment(
        record: TaskAssignment,
        db: AsyncSession,
        user: Any,
        task: Task | None = None,
    ) -> Task | None:
        """Deactivate previous assignments, update task status, notify assignee."""
        task = task or await db.get(Task, record.task_id)
        if not task:
            return None

        old_status = task.status
        now = datetime.utcnow()

        # Deactivate earlier active assignments for this task
        await db.execute(
            update(TaskAssignment)
            .where(
                TaskAssignment.task_id == record.task_id,
                TaskAssignment.id != record.id,
                TaskAssignment.is_active == True,
            )
            .values(is_active=False, unassigned_at=now, status="reassigned")
        )

        new_status = old_status
        if old_status == "pending":
            new_status = "in_progress"
            task.status = new_status

        task.last_modified_by = user.id

        await NotificationService.create_notification(
            db,
            user_id=record.user_id,
            reference_entity="task",
            reference_id=record.task_id,
            type="task_assigned",
            message=f"You have been assigned to task {_task_label(task)}: {task.title}",
            actor_id=user.id,
        )

        if old_status != new_status:
            await AuditLogService.log_event(
                db,
                entity="task",
                record_id=task.id,
                action="update",
                actor_id=user.id,
                old_values={"status": old_status},
                new_values={"status": new_status},
            )

        return task

    @staticmethod
    async def assign_task(
        db: AsyncSession, user: Any, task_id: str, user_id: str
    ) -> TaskAssignment:
        """Assign *task_id* to *user_id* and trigger the assignment side-effects."""
        task = await db.get(Task, task_id)
        if not task:
            raise NotFoundError("Task", task_id)

        if task.status in {"approved", "closed", "cancelled"}:
            raise BadRequestError("Cannot assign a task that is already completed or cancelled")

        assignee = await db.get(User, user_id)
        if not assignee or not assignee.is_active:
            raise NotFoundError("User", user_id)
        project = await db.get(Project, task.project_id)
        if not project:
            raise NotFoundError("Project", task.project_id)
        membership = await db.scalar(
            select(ProjectMember.id).where(
                ProjectMember.project_id == project.id,
                ProjectMember.user_id == user_id,
                ProjectMember.is_active.is_(True),
            )
        )
        if not membership:
            raise BadRequestError("Assignees must be active members of the project")

        meta = MetaRegistry.get("task_assignment")
        naming_service = NamingAppService(NamingRepository(db))
        assignment_id = _id_or_uuid(
            await naming_service.generate_id(meta.naming, "task_assignment")
        )
        idx = await ProjectTaskService.next_assignment_index(db, task_id)
        now = datetime.utcnow()

        data = {
            "id": assignment_id,
            "task_id": task_id,
            "user_id": user_id,
            "idx": idx,
            "assigned_by": user.id,
            "assigned_at": now,
            "is_active": True,
            "status": "active",
            "created_by": user.id,
            "last_modified_by": user.id,
        }

        record = await EntityRepository(db).create("task_assignment", data)
        await ProjectTaskService.post_create_assignment(
            record, db, user, task=task
        )

        await AuditLogService.log_event(
            db,
            entity="task_assignment",
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
    async def list_assignments(
        db: AsyncSession, task_id: str, page: int = 1, page_size: int = 50
    ) -> dict[str, Any]:
        """Return paginated assignments for a task."""
        task = await db.get(Task, task_id)
        if not task:
            raise NotFoundError("Task", task_id)

        q = (
            select(TaskAssignment)
            .where(TaskAssignment.task_id == task_id)
            .order_by(TaskAssignment.idx)
        )
        total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar()
        records = (
            await db.execute(q.offset((page - 1) * page_size).limit(page_size))
        ).scalars().all()

        return {
            "data": [record_to_dict(r) for r in records],
            "total": total,
            "page": page,
            "page_size": page_size,
        }


class TaskSubmissionService:
    """Application helpers for task submissions and revision chains."""

    @staticmethod
    async def next_submission_version(db: AsyncSession, task_assignment_id: str) -> int:
        """Return the next version number for submissions on this assignment."""
        result = await db.execute(
            select(func.max(TaskSubmission.version)).where(
                TaskSubmission.task_assignment_id == task_assignment_id
            )
        )
        return (result.scalar() or 0) + 1

    @staticmethod
    async def create_submission(
        db: AsyncSession, user: Any, data: dict[str, Any]
    ) -> TaskSubmission:
        """Create a task submission against an active assignment.

        Real-world rules:
        - Only the assigned user (or a superuser) can submit.
        - The assignment must be active and the task not already closed.
        - The version is auto-incremented; a ``previous_submission_id`` creates a revision chain.
        - Submitting moves the task to ``for_review`` and notifies the project manager.
        """
        assignment_id = data.get("task_assignment_id")
        assignment = await db.get(TaskAssignment, assignment_id)
        if not assignment:
            raise NotFoundError("Task Assignment", assignment_id)

        if assignment.user_id != user.id and not getattr(user, "is_superuser", False):
            raise ForbiddenError("You can only submit work for tasks assigned to you")
        if assignment.status != "active":
            raise BadRequestError("Cannot submit work for an inactive assignment")

        task = await db.get(Task, assignment.task_id)
        if not task:
            raise NotFoundError("Task", assignment.task_id)
        if task.status in {"approved", "closed", "cancelled"}:
            raise BadRequestError("Cannot submit work for a completed or cancelled task")
        if task.status not in {"in_progress", "needs_revision"}:
            raise BadRequestError(
                "Work can only be submitted while the task is in progress or needs revision"
            )

        previous_submission_id = data.get("previous_submission_id")
        previous_submission = None
        if previous_submission_id:
            previous_submission = await db.get(TaskSubmission, previous_submission_id)
            if not previous_submission:
                raise NotFoundError("Previous Submission", previous_submission_id)
            if previous_submission.task_assignment_id != assignment_id:
                raise BadRequestError("Previous submission belongs to a different assignment")

        version = await TaskSubmissionService.next_submission_version(db, assignment_id)
        if previous_submission:
            version = max(version, previous_submission.version + 1)

        meta = MetaRegistry.get("task_submission")
        naming_service = NamingAppService(NamingRepository(db))
        submission_id = _id_or_uuid(
            await naming_service.generate_id(meta.naming, "task_submission")
        )

        now = datetime.utcnow()
        model = get_entity_model("task_submission")
        data = EntityService.coerce_incoming_types(model, data)
        data.update(
            {
                "id": submission_id,
                "task_assignment_id": assignment_id,
                "version": version,
                "previous_submission_id": previous_submission_id,
                "submitted_by": user.id,
                "submitted_at": now,
                "status": "submitted",
                "created_by": user.id,
                "last_modified_by": user.id,
            }
        )

        record = await EntityRepository(db).create("task_submission", data)
        old_task_status = task.status
        task.status = "for_review"
        task.last_modified_by = user.id

        await AuditLogService.log_event(
            db,
            entity="task_submission",
            record_id=record.id,
            action="submit",
            actor_id=user.id,
            old_values=None,
            new_values=record_to_dict(record),
        )
        if old_task_status != task.status:
            await AuditLogService.log_event(
                db,
                entity="task",
                record_id=task.id,
                action="update",
                actor_id=user.id,
                old_values={"status": old_task_status},
                new_values={"status": task.status},
            )

        project = await db.get(Project, task.project_id)
        manager_id = project.manager_id if project else None
        if manager_id:
            await NotificationService.create_notification(
                db,
                user_id=manager_id,
                reference_entity="task_submission",
                reference_id=record.id,
                type="submission_reviewed",
                message=f"New submission (v{version}) for task {_task_label(task)}: {task.title}",
                actor_id=user.id,
            )

        await db.commit()
        await db.refresh(record)
        return record


class TaskApprovalService:
    """Application helpers for reviewing and approving task submissions."""

    @staticmethod
    async def next_approval_index(db: AsyncSession, submission_id: str) -> int:
        """Return the next approval index for a submission."""
        result = await db.execute(
            select(func.max(TaskApproval.idx)).where(
                TaskApproval.task_submission_id == submission_id
            )
        )
        return (result.scalar() or 0) + 1

    @staticmethod
    def _resolve_task_status(decision: str) -> str:
        if decision == "approved":
            return "approved"
        if decision == "needs_revision":
            return "needs_revision"
        if decision == "rejected":
            return "in_progress"
        raise BadRequestError("Invalid approval decision")

    @staticmethod
    async def create_approval(
        db: AsyncSession,
        user: Any,
        submission_id: str,
        decision: str,
        remarks: str | None = None,
    ) -> TaskApproval:
        """Record a review decision and update related statuses.

        Real-world rules:
        - Decisions are ``approved``, ``rejected``, or ``needs_revision``.
        - Remarks are mandatory for rejection or revision requests.
        - Finalized submissions cannot be reviewed again.
        - Approval credits the user in the Ledger.
        - Every decision writes an AuditLog and notifies the user.
        """
        if decision not in {"approved", "rejected", "needs_revision"}:
            raise BadRequestError("Decision must be approved, rejected, or needs_revision")
        if decision in {"rejected", "needs_revision"} and not remarks:
            raise BadRequestError("Remarks are required for rejected or needs_revision decisions")

        submission = await db.get(TaskSubmission, submission_id)
        if not submission:
            raise NotFoundError("Task Submission", submission_id)
        if submission.status in {"approved", "rejected"}:
            raise BadRequestError("Submission has already been finalized")

        assignment = await db.get(TaskAssignment, submission.task_assignment_id)
        if not assignment:
            raise NotFoundError("Task Assignment", submission.task_assignment_id)
        task = await db.get(Task, assignment.task_id)
        if not task:
            raise NotFoundError("Task", assignment.task_id)

        idx = await TaskApprovalService.next_approval_index(db, submission_id)
        meta = MetaRegistry.get("task_approval")
        naming_service = NamingAppService(NamingRepository(db))
        approval_id = _id_or_uuid(
            await naming_service.generate_id(meta.naming, "task_approval")
        )
        now = datetime.utcnow()

        data = {
            "id": approval_id,
            "task_submission_id": submission_id,
            "idx": idx,
            "approver_id": user.id,
            "decision": decision,
            "remarks": remarks,
            "decided_at": now,
            "created_by": user.id,
            "last_modified_by": user.id,
        }
        record = await EntityRepository(db).create("task_approval", data)

        old_submission_status = submission.status
        submission.status = decision
        submission.last_modified_by = user.id

        old_task_status = task.status
        new_task_status = TaskApprovalService._resolve_task_status(decision)
        if task.status != new_task_status:
            task.status = new_task_status
            task.last_modified_by = user.id

        if decision == "approved":
            await LedgerService.create_ledger_entry(
                db,
                reference_entity="task_submission",
                reference_id=submission.id,
                user_id=assignment.user_id,
                amount=await TaskApprovalService._calculate_submission_amount(db, task, submission),
                entry_type="credit",
                description=f"Credit for approved submission {submission.id} on task {_task_label(task)}",
                period=datetime.utcnow().date(),
                created_by=user.id,
            )

        await AuditLogService.log_event(
            db,
            entity="task_submission",
            record_id=submission.id,
            action="update",
            actor_id=user.id,
            old_values={"status": old_submission_status},
            new_values={"status": submission.status},
        )
        if old_task_status != task.status:
            await AuditLogService.log_event(
                db,
                entity="task",
                record_id=task.id,
                action="update",
                actor_id=user.id,
                old_values={"status": old_task_status},
                new_values={"status": task.status},
            )

        await NotificationService.create_notification(
            db,
            user_id=assignment.user_id,
            reference_entity="task_submission",
            reference_id=submission.id,
            type="revision_requested" if decision == "needs_revision" else "submission_reviewed",
            message=TaskApprovalService._notification_message(decision, task, submission, remarks),
            actor_id=user.id,
        )

        await db.commit()
        await db.refresh(record)
        return record

    @staticmethod
    async def _calculate_submission_amount(
        db: AsyncSession, task: Task, submission: TaskSubmission
    ) -> float:
        task_type = await db.get(TaskType, task.task_type_id)
        rate = float(task_type.unit_rate) if task_type and task_type.unit_rate is not None else 0.0
        quantity = 1.0
        return round(rate * quantity, 2)

    @staticmethod
    def _notification_message(
        decision: str, task: Task, submission: TaskSubmission, remarks: str | None
    ) -> str:
        base = f"Your submission for task {_task_label(task)}: {task.title} was {decision}."
        if remarks:
            return f"{base} Remarks: {remarks}"
        return base
