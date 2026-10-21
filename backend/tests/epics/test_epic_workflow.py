"""Real-world workflow tests for the active project, payroll, and audit epics.

These tests exercise the core domain services end-to-end: project managers create
and assign tasks, users submit work, reviewers approve or reject submissions,
HR generates and pays payroll, and audit/ledger records remain immutable.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select

from app.core.exceptions import BadRequestError
from app.core.framework.models.auth import Role, User
from app.core.security import get_password_hash
from app.infrastructure.database.repositories.entity_repository import EntityRepository
from app.modules.collaboration_audit.models import Ledger, Notification, OcAuditLog

from app.modules.payroll.models import PayrollEntry, PayrollLineItem, PayrollPeriod
from app.modules.payroll.services import PayrollService
from app.modules.project_tasks.models import (
    Project,
    ProjectMember,
    Task,
    TaskApproval,
    TaskAssignment,
    TaskSubmission,
    TaskType,
)
from app.modules.project_tasks.services import (
    ProjectTaskService,
    TaskApprovalService,
    TaskSubmissionService,
)
from app.modules.workspaces.models import WorkspaceMembership


@pytest_asyncio.fixture(autouse=True)
async def _init_test_database(db_engine):
    """Recreate tables for each test so prior test runs do not pollute state."""
    from app.core.database import Base
    async with db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield


def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:10]}"


async def _make_user(db_session, username: str, email: str, roles: list[Role]) -> User:
    user = User(
        id=str(uuid4()),
        username=username,
        email=email,
        full_name=username,
        hashed_password=get_password_hash("secret123"),
        is_active=True,
        is_superuser=False,
    )
    for role in roles:
        user.roles.append(role)
    db_session.add(user)
    await db_session.flush()
    return user


async def _seed_roles(db_session) -> tuple[Role, Role, Role]:
    """Return (user_role, pm_role, hr_role) with unique names per test run."""
    user_role = Role(id=_unique("role"), name=_unique("User"), description="User", is_active=True)
    pm_role = Role(id=_unique("role"), name=_unique("ProjectManager"), description="Project Manager", is_active=True)
    hr_role = Role(id=_unique("role"), name=_unique("HR"), description="HR", is_active=True)
    db_session.add_all([user_role, pm_role, hr_role])
    await db_session.flush()
    return user_role, pm_role, hr_role


async def _make_workspace(db_session):
    from app.modules.workspaces.models.workspace import Workspace

    workspace = Workspace(
        id=_unique("workspace"),
        name=_unique("Workspace"),
        slug=_unique("ws"),
        color="#6366f1",
        timezone="UTC",
        is_active=True,
    )
    db_session.add(workspace)
    await db_session.flush()
    return workspace


async def _make_project(db_session, pm_user: User, workspace) -> Project:
    repo = EntityRepository(db_session)
    data = {
        "id": _unique("proj"),
        "name": _unique("Project"),
        "description": "Real-world test project",
        "manager_id": pm_user.id,
        "workspace_id": workspace.id,
        "status": "active",
        "start_date": date.today(),
        "end_date": date.today() + timedelta(days=30),
        "created_by": pm_user.id,
        "last_modified_by": pm_user.id,
    }
    return await repo.create("project", data)


async def _make_task_type(db_session, pm_user: User, workspace) -> TaskType:
    repo = EntityRepository(db_session)
    data = {
        "id": _unique("tt"),
        "name": _unique("Data Entry"),
        "description": "Data entry task",
        "unit_rate": Decimal("25.00"),
        "unit": "per_task",
        "workspace_id": workspace.id,
        "requires_approval": True,
        "created_by": pm_user.id,
        "last_modified_by": pm_user.id,
    }
    return await repo.create("task_type", data)


async def _make_task(db_session, pm_user: User, project: Project, task_type: TaskType) -> Task:
    data = {
        "project_id": project.id,
        "task_type_id": task_type.id,
        "title": _unique("Task"),
        "description": "A real task",
        "priority": "medium",
        "due_date": datetime.utcnow() + timedelta(days=7),
    }
    return await ProjectTaskService.create_task(db_session, pm_user, data)


@pytest_asyncio.fixture
async def roles(db_session):
    return await _seed_roles(db_session)


@pytest_asyncio.fixture
async def worker_user(db_session, roles):
    _, _, _ = roles
    user_role = roles[0]
    user = await _make_user(db_session, _unique("empuser"), f"{_unique('user')}@example.com", [user_role])
    return user


@pytest_asyncio.fixture
async def pm_user(db_session, roles):
    pm_role = roles[1]
    return await _make_user(db_session, _unique("pmuser"), f"{_unique('pm')}@example.com", [pm_role])


@pytest_asyncio.fixture
async def hr_user(db_session, roles):
    hr_role = roles[2]
    return await _make_user(db_session, _unique("hruser"), f"{_unique('hr')}@example.com", [hr_role])


@pytest_asyncio.fixture
async def workspace(db_session):
    return await _make_workspace(db_session)


@pytest_asyncio.fixture
async def project(db_session, pm_user, workspace):
    return await _make_project(db_session, pm_user, workspace)


@pytest_asyncio.fixture
async def task_type(db_session, pm_user, workspace):
    return await _make_task_type(db_session, pm_user, workspace)


@pytest_asyncio.fixture
async def task(db_session, pm_user, project, task_type):
    return await _make_task(db_session, pm_user, project, task_type)


@pytest_asyncio.fixture
async def assignment(db_session, pm_user, worker_user, task):
    workspace_id = (await db_session.get(Project, task.project_id)).workspace_id
    db_session.add(
        WorkspaceMembership(
            id=_unique("membership"),
            workspace_id=workspace_id,
            user_id=worker_user.id,
            membership_role="member",
            is_home=True,
            is_active=True,
        )
    )
    db_session.add(
        ProjectMember(
            id=_unique("member"),
            project_id=task.project_id,
            user_id=worker_user.id,
            role="member",
            is_active=True,
        )
    )
    await db_session.flush()
    return await ProjectTaskService.assign_task(db_session, pm_user, task.id, worker_user.id)


@pytest.mark.asyncio
async def test_assignment_deactivates_previous_and_moves_task_to_in_progress(
    db_session, pm_user, worker_user, task
):
    project = await db_session.get(Project, task.project_id)
    db_session.add(
        WorkspaceMembership(
            id=_unique("membership"),
            workspace_id=project.workspace_id,
            user_id=worker_user.id,
            membership_role="member",
            is_home=True,
            is_active=True,
        )
    )
    db_session.add(
        ProjectMember(
            id=_unique("member"),
            project_id=task.project_id,
            user_id=worker_user.id,
            role="member",
            is_active=True,
        )
    )
    await db_session.flush()
    first = await ProjectTaskService.assign_task(db_session, pm_user, task.id, worker_user.id)
    second = await ProjectTaskService.assign_task(db_session, pm_user, task.id, worker_user.id)

    await db_session.refresh(first)
    assert first.is_active is False
    assert first.status == "reassigned"
    assert second.is_active is True
    assert second.status == "active"

    await db_session.refresh(task)
    assert task.status == "in_progress"

    note_result = await db_session.execute(
        select(Notification).where(
            Notification.user_id == worker_user.id,
            Notification.reference_entity == "task",
            Notification.reference_id == task.id,
        )
    )
    notes = note_result.scalars().all()
    assert len(notes) >= 1


@pytest.mark.asyncio
async def test_submission_rejected_for_non_assignee(
    db_session, pm_user, hr_user, assignment
):
    with pytest.raises(Exception) as exc_info:
        await TaskSubmissionService.create_submission(
            db_session, hr_user, {"task_assignment_id": assignment.id, "notes": "Hijacked"}
        )
    assert "only submit" in str(exc_info.value).lower() or "assigned" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_submission_creates_version_and_moves_task_to_for_review(
    db_session, worker_user, assignment, task
):
    submission = await TaskSubmissionService.create_submission(
        db_session, worker_user, {"task_assignment_id": assignment.id, "notes": "First draft"}
    )

    assert submission.version == 1
    assert submission.status == "submitted"
    assert submission.previous_submission_id is None

    await db_session.refresh(task)
    assert task.status == "for_review"

    audit = await db_session.execute(
        select(OcAuditLog).where(
            OcAuditLog.reference_entity == "task_submission",
            OcAuditLog.reference_id == submission.id,
            OcAuditLog.action == "submit",
        )
    )
    assert audit.scalar_one_or_none() is not None
    with pytest.raises(BadRequestError, match="only be submitted"):
        await TaskSubmissionService.create_submission(
            db_session, worker_user, {"task_assignment_id": assignment.id, "notes": "Duplicate"}
        )


@pytest.mark.asyncio
async def test_revision_chain_increments_version(
    db_session, worker_user, assignment, task
):
    first = await TaskSubmissionService.create_submission(
        db_session, worker_user, {"task_assignment_id": assignment.id, "notes": "v1"}
    )
    await TaskApprovalService.create_approval(
        db_session, worker_user, first.id, "needs_revision", remarks="Fix formatting"
    )

    second = await TaskSubmissionService.create_submission(
        db_session,
        worker_user,
        {
            "task_assignment_id": assignment.id,
            "previous_submission_id": first.id,
            "notes": "v2",
        },
    )

    assert second.version == 2
    assert second.previous_submission_id == first.id
    assert second.status == "submitted"


@pytest.mark.asyncio
async def test_approval_approved_creates_ledger_credit_and_notifies(
    db_session, pm_user, worker_user, assignment, task, task_type
):
    submission = await TaskSubmissionService.create_submission(
        db_session, worker_user, {"task_assignment_id": assignment.id, "notes": "Done"}
    )

    approval = await TaskApprovalService.create_approval(
        db_session, pm_user, submission.id, "approved"
    )
    assert approval.decision == "approved"

    await db_session.refresh(submission)
    await db_session.refresh(task)
    assert submission.status == "approved"
    assert task.status == "approved"

    ledger = await db_session.execute(
        select(Ledger).where(
            Ledger.reference_entity == "task_submission",
            Ledger.reference_id == submission.id,
            Ledger.entry_type == "credit",
        )
    )
    entry = ledger.scalar_one_or_none()
    assert entry is not None
    assert float(entry.amount) == float(task_type.unit_rate)
    assert entry.user_id == worker_user.id

    note = await db_session.execute(
        select(Notification).where(
            Notification.user_id == worker_user.id,
            Notification.reference_entity == "task_submission",
            Notification.reference_id == submission.id,
        )
    )
    assert note.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_approval_rejected_returns_task_to_in_progress(
    db_session, pm_user, worker_user, assignment, task
):
    submission = await TaskSubmissionService.create_submission(
        db_session, worker_user, {"task_assignment_id": assignment.id, "notes": "Done"}
    )

    await TaskApprovalService.create_approval(
        db_session, pm_user, submission.id, "rejected", remarks="Does not meet requirements"
    )

    await db_session.refresh(submission)
    await db_session.refresh(task)
    assert submission.status == "rejected"
    assert task.status == "in_progress"

    ledger = await db_session.execute(
        select(Ledger).where(
            Ledger.reference_entity == "task_submission",
            Ledger.reference_id == submission.id,
        )
    )
    assert ledger.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_payroll_generation_excludes_unapproved_submissions(
    db_session, pm_user, hr_user, worker_user, assignment, task, task_type, project
):
    approved_sub = await TaskSubmissionService.create_submission(
        db_session, worker_user, {"task_assignment_id": assignment.id, "notes": "Approved work"}
    )
    await TaskApprovalService.create_approval(db_session, pm_user, approved_sub.id, "approved")

    # Create a separate task and assignment with a submission that is never approved
    other_task = await _make_task(db_session, pm_user, project, task_type)
    other_assignment = await ProjectTaskService.assign_task(
        db_session, pm_user, other_task.id, worker_user.id
    )
    await TaskSubmissionService.create_submission(
        db_session, worker_user, {"task_assignment_id": other_assignment.id, "notes": "Draft"}
    )

    period = await PayrollService.create_payroll_period(
        db_session,
        hr_user,
        {
            "period_type": "bi_monthly",
            "start_date": date.today() - timedelta(days=5),
            "end_date": date.today() + timedelta(days=5),
            "cutoff": date.today() + timedelta(days=5),
        },
    )

    entries = await PayrollService.generate_payroll(db_session, hr_user, period.id)
    assert len(entries) == 1
    entry = entries[0]
    assert entry.user_id == worker_user.id
    assert entry.total_tasks == 1
    assert float(entry.total_amount) == float(task_type.unit_rate)

    line_items = await db_session.execute(
        select(PayrollLineItem).where(
            PayrollLineItem.payroll_entry_id == entry.id
        )
    )
    items = line_items.scalars().all()
    assert len(items) == 1
    assert float(items[0].amount) == float(task_type.unit_rate)
    assert float(items[0].quantity) == 1.0


@pytest.mark.asyncio
async def test_payroll_payment_creates_ledger_debit_and_updates_status(
    db_session, pm_user, hr_user, worker_user, assignment, task, task_type
):
    approved_sub = await TaskSubmissionService.create_submission(
        db_session, worker_user, {"task_assignment_id": assignment.id, "notes": "Approved"}
    )
    await TaskApprovalService.create_approval(db_session, pm_user, approved_sub.id, "approved")

    period = await PayrollService.create_payroll_period(
        db_session,
        hr_user,
        {
            "period_type": "bi_monthly",
            "start_date": date.today() - timedelta(days=5),
            "end_date": date.today() + timedelta(days=5),
            "cutoff": date.today() + timedelta(days=5),
        },
    )

    entries = await PayrollService.generate_payroll(db_session, hr_user, period.id)
    entry = entries[0]
    entry = await PayrollService.approve_payroll_entry(db_session, hr_user, entry.id)
    entry = await PayrollService.pay_payroll_entry(db_session, hr_user, entry.id)

    assert entry.status == "paid"

    debit = await db_session.execute(
        select(Ledger).where(
            Ledger.reference_entity == "payroll_entry",
            Ledger.reference_id == entry.id,
            Ledger.entry_type == "debit",
        )
    )
    ledger_entry = debit.scalar_one_or_none()
    assert ledger_entry is not None
    assert float(ledger_entry.amount) == float(entry.total_amount)
    assert ledger_entry.user_id == worker_user.id

    await db_session.refresh(period)
    assert period.status == "paid"


@pytest.mark.asyncio
async def test_payroll_regeneration_is_blocked_after_entry_approval(
    db_session, pm_user, hr_user, worker_user, assignment, task
):
    submission = await TaskSubmissionService.create_submission(
        db_session, worker_user, {"task_assignment_id": assignment.id, "notes": "Ready"}
    )
    await TaskApprovalService.create_approval(
        db_session, pm_user, submission.id, "approved"
    )
    period = await PayrollService.create_payroll_period(
        db_session,
        hr_user,
        {
            "start_date": date.today() - timedelta(days=5),
            "end_date": date.today() + timedelta(days=5),
        },
    )
    entry = (await PayrollService.generate_payroll(db_session, hr_user, period.id))[0]
    await PayrollService.approve_payroll_entry(db_session, hr_user, entry.id)

    with pytest.raises(BadRequestError, match="Cannot regenerate payroll"):
        await PayrollService.generate_payroll(db_session, hr_user, period.id)


@pytest.mark.asyncio
async def test_period_is_paid_only_after_all_employee_entries_are_paid(
    db_session, pm_user, hr_user, worker_user, assignment, project, task_type
):
    second_task = await _make_task(db_session, pm_user, project, task_type)
    db_session.add(
        WorkspaceMembership(
            id=_unique("membership"),
            workspace_id=project.workspace_id,
            user_id=hr_user.id,
            membership_role="member",
            is_home=True,
            is_active=True,
        )
    )
    db_session.add(
        ProjectMember(
            id=_unique("member"),
            project_id=project.id,
            user_id=hr_user.id,
            role="member",
            is_active=True,
        )
    )
    await db_session.flush()
    second_assignment = await ProjectTaskService.assign_task(
        db_session, pm_user, second_task.id, hr_user.id
    )
    for assignee, task_assignment in (
        (worker_user, assignment),
        (hr_user, second_assignment),
    ):
        submission = await TaskSubmissionService.create_submission(
            db_session,
            assignee,
            {"task_assignment_id": task_assignment.id, "notes": "Approved work"},
        )
        await TaskApprovalService.create_approval(
            db_session, pm_user, submission.id, "approved"
        )

    period = await PayrollService.create_payroll_period(
        db_session,
        hr_user,
        {
            "start_date": date.today() - timedelta(days=5),
            "end_date": date.today() + timedelta(days=5),
        },
    )
    entries = await PayrollService.generate_payroll(db_session, hr_user, period.id)
    assert len(entries) == 2

    for entry in entries:
        await PayrollService.approve_payroll_entry(db_session, hr_user, entry.id)
    await PayrollService.pay_payroll_entry(db_session, hr_user, entries[0].id)
    await db_session.refresh(period)
    assert period.status == "open"

    await PayrollService.pay_payroll_entry(db_session, hr_user, entries[1].id)
    await db_session.refresh(period)
    assert period.status == "paid"


@pytest.mark.asyncio
async def test_audit_log_and_ledger_update_delete_rejected_via_entity_api(
    db_session, superuser_client
):
    """Audit and ledger records are immutable through the generic CRUD API."""
    audit = OcAuditLog(
        id=_unique("audit"),
        reference_entity="task",
        reference_id="TASK-001",
        action="create",
        actor_id="Administrator",
        timestamp=datetime.utcnow(),
        created_by="Administrator",
        last_modified_by="Administrator",
    )
    db_session.add(audit)
    await db_session.flush()

    ledger = Ledger(
        id=_unique("led"),
        reference_entity="payroll_entry",
        reference_id="PE-001",
        user_id="Administrator",
        amount=Decimal("100.00"),
        entry_type="credit",
        description="Test",
        period=date.today(),
        created_by="Administrator",
        last_modified_by="Administrator",
    )
    db_session.add(ledger)
    await db_session.flush()

    update_response = await superuser_client.put(
        f"/api/entity/oc_audit_log/{audit.id}",
        json={"data": {"reference_entity": "tampered"}},
    )
    assert update_response.status_code == 403
    assert update_response.json()["status"] == "error"
    assert "immutable" in update_response.json()["message"].lower()

    delete_response = await superuser_client.delete(f"/api/entity/ledger/{ledger.id}")
    assert delete_response.status_code == 403
    assert delete_response.json()["status"] == "error"
    assert "immutable" in delete_response.json()["message"].lower()
