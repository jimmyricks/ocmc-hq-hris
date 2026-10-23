from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy import func, select

from app.core.exceptions import BadRequestError, ConflictError, ForbiddenError
from app.core.framework.models.auth import User
from app.core.framework.models.infrastructure import WorkflowLedger
from app.application.services.access_control.row_scope_service import RowScopeService
from app.api.app.payroll import _require_payroll_admin
from app.modules.collaboration_audit.models import Ledger
from app.modules.payroll.models import (
    Invoice,
    PayrollEntry,
    PayrollLineItem,
    PayrollPeriod,
    UserTaskRate,
)
from app.modules.payroll.services import PayrollService
from app.modules.project_tasks.models import (
    Project,
    Task,
    TaskAssignment,
    TaskSubmission,
    TaskType,
)
from app.modules.project_tasks.services import TaskApprovalService
from app.modules.workspaces.models import Workspace, WorkspaceMembership
from app.modules.workspaces.services import WorkspaceService


@pytest.mark.parametrize(
    ("year", "month", "last_day"),
    [(2026, 2, 28), (2028, 2, 29), (2026, 4, 30), (2026, 10, 31)],
)
def test_bi_monthly_periods_cover_both_halves_of_calendar_month(year, month, last_day):
    first, second = PayrollService.bi_monthly_periods(year, month)
    assert first["start_date"] == date(year, month, 1)
    assert first["end_date"] == first["cutoff"] == date(year, month, 14)
    assert second["start_date"] == date(year, month, 15)
    assert second["end_date"] == second["cutoff"] == date(year, month, last_day)


@pytest.mark.asyncio
async def test_period_creation_enforces_canonical_ranges_and_rejects_overlap(
    db_session, authenticated_user
):
    with pytest.raises(BadRequestError, match="days 1–14"):
        await PayrollService.create_payroll_period(
            db_session,
            authenticated_user,
            {
                "start_date": date(2026, 10, 1),
                "end_date": date(2026, 10, 15),
            },
        )

    data = {
        "period_type": "bi_monthly",
        "start_date": date(2026, 10, 1),
        "end_date": date(2026, 10, 14),
        "cutoff": date(2026, 10, 14),
    }
    first = await PayrollService.create_payroll_period(
        db_session, authenticated_user, data
    )
    assert first.id
    with pytest.raises(ConflictError, match="already covers"):
        await PayrollService.create_payroll_period(
            db_session, authenticated_user, data
        )


@pytest.mark.asyncio
async def test_employee_rate_override_precedes_workspace_default():
    class RateQuery:
        def __init__(self, value):
            self.value = value

        async def scalar(self, _query):
            return self.value

    task_type = SimpleNamespace(
        id="type-x",
        workspace_id="workspace-bahandi",
        unit_rate=Decimal("100.00"),
        unit="per_task",
    )
    override = SimpleNamespace(rate=Decimal("125.50"))
    assert await PayrollService.resolve_rate(
        RateQuery(override), task_type, "workspace-bahandi", "employee-a"
    ) == Decimal("125.50")
    assert await PayrollService.resolve_rate(
        RateQuery(None), task_type, "workspace-bahandi", "employee-b"
    ) == Decimal("100.00")


def test_payroll_snapshot_uses_decimal_rounding_and_one_deliverable():
    assert PayrollService.resolve_snapshot(Decimal("125.505")) == (
        Decimal("125.51"),
        Decimal("1.00"),
        Decimal("125.51"),
    )
    with pytest.raises(BadRequestError, match="one approved deliverable"):
        PayrollService.resolve_snapshot(Decimal("50"), Decimal("2"))


def test_payroll_requires_hr_or_system_admin_for_employee_rates():
    _require_payroll_admin(
        SimpleNamespace(roles=["HR"], is_superuser=False)
    )
    _require_payroll_admin(
        SimpleNamespace(roles=[], is_superuser=True)
    )
    with pytest.raises(ForbiddenError):
        _require_payroll_admin(
            SimpleNamespace(roles=["ProjectManager"], is_superuser=False)
        )


@pytest.mark.asyncio
async def test_hr_payroll_uses_dedicated_global_paths_not_generic_line_items():
    class RBAC:
        pass

    scope = RowScopeService(
        db=None,
        rbac_service=RBAC(),
        meta_registry=None,
        workflow_repo=None,
    )
    query = await scope.apply_scope_to_query(
        select(PayrollLineItem),
        PayrollLineItem,
        "payroll_line_item",
        user_id="hr-user",
        role_ids=[],
        role_names=["HR"],
        is_superuser=False,
    )

    assert "WHERE false" in str(query)
    assert WorkspaceService.is_payroll_admin(["HR"], False)
    assert not WorkspaceService.is_admin(["HR"], False)


@pytest.mark.asyncio
async def test_payroll_line_items_cannot_be_mutated_through_generic_crud():
    class RBAC:
        pass

    scope = RowScopeService(
        db=None,
        rbac_service=RBAC(),
        meta_registry=None,
        workflow_repo=None,
    )
    user = SimpleNamespace(id="hr-user", roles=["HR"], is_superuser=False)

    with pytest.raises(ForbiddenError, match="managed by payroll generation"):
        await scope.prepare_create_data("payroll_line_item", {}, user)
    with pytest.raises(ForbiddenError, match="managed by payroll generation"):
        await scope.authorize_record_write(
            "payroll_line_item", PayrollLineItem(), {}, user
        )
    with pytest.raises(ForbiddenError, match="payroll rates API"):
        await scope.prepare_create_data("user_task_rate", {}, user)
    with pytest.raises(ForbiddenError, match="payroll rates API"):
        await scope.authorize_record_write("user_task_rate", UserTaskRate(), {}, user)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("task_type", "workspace_id", "message"),
    [
        (SimpleNamespace(id="x", workspace_id="a", unit_rate=125, unit="per_task"), None, "Map the project"),
        (SimpleNamespace(id="x", workspace_id=None, unit_rate=125, unit="per_task"), "a", "Map the task type"),
        (None, "a", "Map the task type"),
        (SimpleNamespace(id="x", workspace_id="a", unit_rate=0, unit="per_task"), "a", "positive"),
        (SimpleNamespace(id="x", workspace_id="a", unit_rate=125, unit="per_hour"), "a", "captured hours"),
    ],
)
async def test_payroll_rejects_invalid_workspace_or_unit_rates(
    task_type, workspace_id, message
):
    class NoRate:
        async def scalar(self, _query):
            return None

    with pytest.raises(BadRequestError, match=message):
        await PayrollService.resolve_rate(NoRate(), task_type, workspace_id, "user")


@pytest.mark.asyncio
async def test_approval_snapshot_survives_rate_change_and_payroll_replay(
    db_session, authenticated_user, record_id_factory
):
    employee = authenticated_user
    workspace_id = record_id_factory("workspace")
    workspace = Workspace(
        id=workspace_id,
        name="Test Company",
        slug=record_id_factory("test-company"),
        color="#336699",
        timezone="UTC",
        is_active=True,
    )
    membership = WorkspaceMembership(
        id=record_id_factory("membership"),
        workspace_id=workspace_id,
        user_id=employee.id,
        membership_role="member",
        is_home=True,
        is_active=True,
    )
    project = Project(
        id=record_id_factory("project"),
        name="Payroll snapshot project",
        workspace_id=workspace_id,
        manager_id=employee.id,
    )
    task_type = TaskType(
        id=record_id_factory("type"),
        name="Same Task Type",
        workspace_id=workspace_id,
        unit_rate=Decimal("100.00"),
        unit="per_task",
    )
    override = UserTaskRate(
        id=record_id_factory("rate"),
        workspace_id=workspace_id,
        task_type_id=task_type.id,
        user_id=employee.id,
        rate=Decimal("125.50"),
    )
    task = Task(
        id=record_id_factory("task"),
        project_id=project.id,
        workspace_id=workspace_id,
        task_type_id=task_type.id,
        title="Deliverable",
        status="for_review",
    )
    assignment = TaskAssignment(
        id=record_id_factory("assignment"),
        task_id=task.id,
        user_id=employee.id,
        assigned_by=employee.id,
        idx=1,
        assigned_at=datetime(2026, 10, 5, 12),
        is_active=True,
        status="active",
    )
    submitted_at = datetime(2026, 10, 8, 12)
    submission = TaskSubmission(
        id=record_id_factory("submission"),
        task_assignment_id=assignment.id,
        version=1,
        status="submitted",
        submitted_by=employee.id,
        submitted_at=submitted_at,
    )
    db_session.add_all(
        [workspace, membership, project, task_type, override, task, assignment, submission]
    )
    await db_session.flush()

    await TaskApprovalService.create_approval(
        db_session, employee, submission.id, "approved"
    )
    task.status = "done"
    db_session.add(
        WorkflowLedger(
            entity_type="task",
            record_id=task.id,
            previous_state="approved",
            next_state="done",
            changed_at=datetime(2026, 10, 8, 13),
        )
    )
    await db_session.refresh(submission)
    assert submission.approved_rate == Decimal("125.50")
    assert submission.approved_quantity == Decimal("1.00")
    assert submission.approved_amount == Decimal("125.50")
    credit = await db_session.scalar(
        select(Ledger).where(
            Ledger.reference_entity == "task_submission",
            Ledger.reference_id == submission.id,
            Ledger.entry_type == "credit",
        )
    )
    assert credit.amount == Decimal("125.50")

    # Later edits apply to future approvals only.
    override.rate = Decimal("250.00")
    late_task = Task(
        id=record_id_factory("task"),
        project_id=project.id,
        workspace_id=workspace_id,
        task_type_id=task_type.id,
        title="Outside cutoff",
        status="done",
    )
    late_assignment = TaskAssignment(
        id=record_id_factory("assignment"),
        task_id=late_task.id,
        user_id=employee.id,
        assigned_by=employee.id,
        idx=1,
        assigned_at=datetime(2026, 10, 11, 12),
        is_active=True,
        status="active",
    )
    late_submission = TaskSubmission(
        id=record_id_factory("submission"),
        task_assignment_id=late_assignment.id,
        version=1,
        status="approved",
        submitted_by=employee.id,
        submitted_at=datetime(2026, 10, 11, 12),
        approved_rate=Decimal("250.00"),
        approved_quantity=Decimal("1.00"),
        approved_amount=Decimal("250.00"),
    )
    not_done_task = Task(
        id=record_id_factory("task"),
        project_id=project.id,
        workspace_id=workspace_id,
        task_type_id=task_type.id,
        title="Approved but not Done",
        status="approved",
    )
    not_done_assignment = TaskAssignment(
        id=record_id_factory("assignment"),
        task_id=not_done_task.id,
        user_id=employee.id,
        assigned_by=employee.id,
        idx=1,
        assigned_at=datetime(2026, 10, 11, 12),
        is_active=True,
        status="active",
    )
    not_done_submission = TaskSubmission(
        id=record_id_factory("submission"),
        task_assignment_id=not_done_assignment.id,
        version=1,
        status="approved",
        submitted_by=employee.id,
        submitted_at=datetime(2026, 10, 11, 12),
        approved_rate=Decimal("250.00"),
        approved_quantity=Decimal("1.00"),
        approved_amount=Decimal("250.00"),
    )
    db_session.add_all(
        [
            late_task,
            late_assignment,
            late_submission,
            not_done_task,
            not_done_assignment,
            not_done_submission,
            WorkflowLedger(
                entity_type="task",
                record_id=late_task.id,
                previous_state="approved",
                next_state="done",
                changed_at=datetime(2026, 10, 15, 12),
            ),
        ]
    )
    period = PayrollPeriod(
        id=record_id_factory("period"),
        label="October cutoff",
        period_type="bi_monthly",
        start_date=date(2026, 10, 1),
        end_date=date(2026, 10, 14),
        cutoff=date(2026, 10, 14),
        status="open",
    )
    db_session.add(period)
    await db_session.flush()

    entries = await PayrollService.generate_payroll(
        db_session, employee, period.id
    )
    assert len(entries) == 1
    assert entries[0].payroll_period_id == period.id
    assert entries[0].total_amount == Decimal("125.50")
    line = await db_session.scalar(
        select(PayrollLineItem).where(PayrollLineItem.payroll_entry_id == entries[0].id)
    )
    assert line.rate == Decimal("125.50")
    assert line.quantity == Decimal("1.00")
    assert line.amount == Decimal("125.50")
    await db_session.refresh(task)
    assert task.status == "done"

    overlapping_period = PayrollPeriod(
        id=record_id_factory("period"),
        label="Duplicate October cutoff",
        period_type="bi_monthly",
        start_date=date(2026, 10, 1),
        end_date=date(2026, 10, 14),
        cutoff=date(2026, 10, 14),
        status="open",
    )
    db_session.add(overlapping_period)
    await db_session.flush()
    with pytest.raises(BadRequestError, match="another payroll period"):
        await PayrollService.generate_payroll(
            db_session, employee, overlapping_period.id
        )

    await PayrollService.approve_payroll_entry(db_session, employee, entries[0].id)
    invoice = await db_session.scalar(
        select(Invoice).where(Invoice.payroll_entry_id == entries[0].id)
    )
    assert invoice.status == "issued"
    assert invoice.total_amount == Decimal("125.50")
    await PayrollService.pay_payroll_entry(db_session, employee, entries[0].id)
    await db_session.refresh(invoice)
    assert invoice.status == "paid"
    debit = await db_session.scalar(
        select(Ledger).where(
            Ledger.reference_entity == "payroll_entry",
            Ledger.reference_id == entries[0].id,
            Ledger.entry_type == "debit",
        )
    )
    assert invoice.total_amount == Decimal("125.50")
    assert debit.amount == Decimal("125.50")
    with pytest.raises(BadRequestError, match="approved before payment"):
        await PayrollService.pay_payroll_entry(db_session, employee, entries[0].id)
    assert await db_session.scalar(
        select(func.count()).select_from(Invoice).where(
            Invoice.payroll_entry_id == entries[0].id
        )
    ) == 1
    assert await db_session.scalar(
        select(func.count()).select_from(Ledger).where(
            Ledger.reference_entity == "payroll_entry",
            Ledger.reference_id == entries[0].id,
            Ledger.entry_type == "debit",
        )
    ) == 1
    with pytest.raises(BadRequestError, match="paid period"):
        await PayrollService.generate_payroll(db_session, employee, period.id)


@pytest.mark.asyncio
async def test_payroll_calculates_employee_and_workspace_rates_with_decimal_totals(
    db_session, authenticated_user, record_id_factory
):
    employee_a1 = authenticated_user

    def make_user(name: str) -> User:
        suffix = record_id_factory("user")
        return User(
            id=suffix,
            username=f"payroll-{suffix}",
            email=f"{suffix}@example.test",
            full_name=name,
            hashed_password="unused",
            is_active=True,
        )

    employee_a2 = make_user("Employee A2")
    employee_b = make_user("Employee B")
    workspace_a = Workspace(
        id=record_id_factory("workspace"),
        name="Company A",
        slug=record_id_factory("company-a"),
        color="#336699",
        timezone="UTC",
        is_active=True,
    )
    workspace_b = Workspace(
        id=record_id_factory("workspace"),
        name="Company B",
        slug=record_id_factory("company-b"),
        color="#663399",
        timezone="UTC",
        is_active=True,
    )
    project_a = Project(
        id=record_id_factory("project"),
        name="Project A",
        workspace_id=workspace_a.id,
        manager_id=employee_a1.id,
    )
    project_b = Project(
        id=record_id_factory("project"),
        name="Project B",
        workspace_id=workspace_b.id,
        manager_id=employee_b.id,
    )
    type_a_x = TaskType(
        id=record_id_factory("type"),
        name="Type X",
        workspace_id=workspace_a.id,
        unit_rate=Decimal("100.00"),
        unit="per_task",
    )
    type_a_y = TaskType(
        id=record_id_factory("type"),
        name="Type Y",
        workspace_id=workspace_a.id,
        unit_rate=Decimal("30.00"),
        unit="per_task",
    )
    type_b_x = TaskType(
        id=record_id_factory("type"),
        name="Type X",
        workspace_id=workspace_b.id,
        unit_rate=Decimal("100.00"),
        unit="per_task",
    )
    db_session.add_all(
        [
            employee_a2,
            employee_b,
            workspace_a,
            workspace_b,
            project_a,
            project_b,
            type_a_x,
            type_a_y,
            type_b_x,
        ]
    )
    db_session.add_all(
        [
            WorkspaceMembership(
                id=record_id_factory("membership"),
                workspace_id=workspace_a.id,
                user_id=user_id,
                membership_role="member",
                is_home=(user_id == employee_a1.id),
                is_active=True,
            )
            for user_id in (employee_a1.id, employee_a2.id)
        ]
        + [
            WorkspaceMembership(
                id=record_id_factory("membership"),
                workspace_id=workspace_b.id,
                user_id=employee_b.id,
                membership_role="member",
                is_home=True,
                is_active=True,
            )
        ]
    )
    db_session.add_all(
        [
            UserTaskRate(
                id=record_id_factory("rate"),
                workspace_id=workspace_a.id,
                task_type_id=type_a_x.id,
                user_id=employee_a1.id,
                rate=Decimal("125.50"),
            ),
            UserTaskRate(
                id=record_id_factory("rate"),
                workspace_id=workspace_a.id,
                task_type_id=type_a_x.id,
                user_id=employee_a2.id,
                rate=Decimal("80.00"),
            ),
            UserTaskRate(
                id=record_id_factory("rate"),
                workspace_id=workspace_a.id,
                task_type_id=type_a_y.id,
                user_id=employee_a1.id,
                rate=Decimal("40.25"),
            ),
            UserTaskRate(
                id=record_id_factory("rate"),
                workspace_id=workspace_b.id,
                task_type_id=type_b_x.id,
                user_id=employee_b.id,
                rate=Decimal("90.75"),
            ),
        ]
    )

    work = [
        (employee_a1, project_a, type_a_x, Decimal("125.50")),
        (employee_a1, project_a, type_a_x, Decimal("125.50")),
        (employee_a1, project_a, type_a_y, Decimal("40.25")),
        (employee_a2, project_a, type_a_x, Decimal("80.00")),
        (employee_b, project_b, type_b_x, Decimal("90.75")),
    ]
    tasks = []
    for idx, (employee, project, task_type, rate) in enumerate(work, start=1):
        task = Task(
            id=record_id_factory("task"),
            project_id=project.id,
            workspace_id=project.workspace_id,
            task_type_id=task_type.id,
            title=f"Deliverable {idx}",
            status="done",
        )
        assignment = TaskAssignment(
            id=record_id_factory("assignment"),
            task_id=task.id,
            user_id=employee.id,
            assigned_by=employee.id,
            idx=1,
            assigned_at=datetime(2026, 10, 5, 12),
            is_active=False,
            status="completed",
        )
        submission = TaskSubmission(
            id=record_id_factory("submission"),
            task_assignment_id=assignment.id,
            version=1,
            status="approved",
            submitted_by=employee.id,
            submitted_at=datetime(2026, 10, 8, 12),
            approved_rate=rate,
            approved_quantity=Decimal("1.00"),
            approved_amount=rate,
        )
        done_at = (
            datetime(2026, 10, 1)
            if idx == 1
            else datetime(2026, 10, 14, 23, 59, 59)
            if idx == 2
            else datetime(2026, 10, 8, 13)
        )
        db_session.add_all(
            [
                task,
                assignment,
                submission,
                WorkflowLedger(
                    entity_type="task",
                    record_id=task.id,
                    previous_state="approved",
                    next_state="done",
                    changed_at=done_at,
                ),
            ]
        )
        tasks.append(task)

    period = PayrollPeriod(
        id=record_id_factory("period"),
        label="All workspace rates",
        period_type="bi_monthly",
        start_date=date(2026, 10, 1),
        end_date=date(2026, 10, 14),
        cutoff=date(2026, 10, 14),
        status="open",
    )
    db_session.add(period)
    await db_session.flush()

    entries = await PayrollService.generate_payroll(
        db_session, employee_a1, period.id
    )
    assert len(entries) == 3
    assert all(entry.payroll_period_id == period.id for entry in entries)
    assert all(task.status == "done" for task in tasks)
    totals = {entry.user_id: entry.total_amount for entry in entries}
    assert totals == {
        employee_a1.id: Decimal("291.25"),
        employee_a2.id: Decimal("80.00"),
        employee_b.id: Decimal("90.75"),
    }
    assert sum(totals.values()) == Decimal("462.00")

    # Replaying generation replaces draft entries instead of duplicating lines.
    replay = await PayrollService.generate_payroll(db_session, employee_a1, period.id)
    assert len(replay) == 3
    assert await db_session.scalar(
        select(func.count()).select_from(PayrollLineItem).join(
            PayrollEntry, PayrollEntry.id == PayrollLineItem.payroll_entry_id
        ).where(PayrollEntry.payroll_period_id == period.id)
    ) == 5


@pytest.mark.asyncio
async def test_employee_rate_api_validates_workspace_type_and_membership(
    authenticated_client, db_session, authenticated_user, record_id_factory
):
    workspace = Workspace(
        id=record_id_factory("workspace"),
        name="Rate API Workspace",
        slug=record_id_factory("rate-api"),
        color="#336699",
        timezone="UTC",
        is_active=True,
    )
    other_workspace = Workspace(
        id=record_id_factory("workspace"),
        name="Other Workspace",
        slug=record_id_factory("other"),
        color="#663399",
        timezone="UTC",
        is_active=True,
    )
    task_type = TaskType(
        id=record_id_factory("type"),
        name="API Type",
        workspace_id=workspace.id,
        unit_rate=Decimal("100.00"),
        unit="per_task",
    )
    db_session.add_all(
        [
            workspace,
            other_workspace,
            task_type,
            WorkspaceMembership(
                id=record_id_factory("membership"),
                workspace_id=workspace.id,
                user_id=authenticated_user.id,
                membership_role="member",
                is_home=True,
                is_active=True,
            ),
        ]
    )
    await db_session.flush()

    response = await authenticated_client.post(
        "/api/payroll/rates",
        json={
            "workspace_id": workspace.id,
            "task_type_id": task_type.id,
            "user_id": authenticated_user.id,
            "rate": "125.50",
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"]["rate"] == 125.5

    breakdown = await authenticated_client.get(
        f"/api/payroll/hr/users/{authenticated_user.id}/rates"
    )
    assert breakdown.status_code == 200, breakdown.text
    assert breakdown.json()["data"]["rates"][0]["applied_rate"] == 125.5
    summary = await authenticated_client.get("/api/payroll/hr/summary")
    assert summary.status_code == 200, summary.text

    mismatched_workspace = await authenticated_client.post(
        "/api/payroll/rates",
        json={
            "workspace_id": other_workspace.id,
            "task_type_id": task_type.id,
            "user_id": authenticated_user.id,
            "rate": "90.00",
        },
    )
    assert mismatched_workspace.status_code == 400

    duplicate = await authenticated_client.post(
        "/api/payroll/rates",
        json={
            "workspace_id": workspace.id,
            "task_type_id": task_type.id,
            "user_id": authenticated_user.id,
            "rate": "130.00",
        },
    )
    assert duplicate.status_code == 409


@pytest.mark.asyncio
async def test_employee_invoice_endpoint_only_returns_the_current_users_invoices(
    authenticated_client, db_session, authenticated_user, record_id_factory
):
    other_user = User(
        id=record_id_factory("user"),
        username=record_id_factory("other"),
        email=f"{record_id_factory('other')}@example.test",
        full_name="Other Employee",
        hashed_password="unused",
        is_active=True,
    )
    period = PayrollPeriod(
        id=record_id_factory("period"),
        label="October 1–14",
        period_type="bi_monthly",
        start_date=date(2026, 10, 1),
        end_date=date(2026, 10, 14),
        cutoff=date(2026, 10, 14),
        status="open",
    )
    db_session.add_all([other_user, period])
    await db_session.flush()

    own_entry = PayrollEntry(
        id=record_id_factory("entry"),
        payroll_period_id=period.id,
        user_id=authenticated_user.id,
        total_tasks=1,
        total_amount=Decimal("100.00"),
        status="approved",
    )
    other_entry = PayrollEntry(
        id=record_id_factory("entry"),
        payroll_period_id=period.id,
        user_id=other_user.id,
        total_tasks=1,
        total_amount=Decimal("200.00"),
        status="approved",
    )
    db_session.add_all([own_entry, other_entry])
    await db_session.flush()
    own_invoice = Invoice(
        id=record_id_factory("invoice"),
        payroll_entry_id=own_entry.id,
        payroll_period_id=period.id,
        user_id=authenticated_user.id,
        invoice_number="INV-OWN",
        total_tasks=1,
        total_amount=Decimal("100.00"),
        currency="PHP",
        status="issued",
    )
    other_invoice = Invoice(
        id=record_id_factory("invoice"),
        payroll_entry_id=other_entry.id,
        payroll_period_id=period.id,
        user_id=other_user.id,
        invoice_number="INV-OTHER",
        total_tasks=1,
        total_amount=Decimal("200.00"),
        currency="PHP",
        status="issued",
    )
    db_session.add_all([own_invoice, other_invoice])
    await db_session.flush()

    matching_entry = await authenticated_client.get(
        f"/api/payroll/periods/{period.id}/entries/{own_entry.id}"
    )
    mismatched_entry = await authenticated_client.get(
        f"/api/payroll/periods/{record_id_factory('period')}/entries/{own_entry.id}"
    )
    response = await authenticated_client.get("/api/payroll/my-invoices")

    assert matching_entry.status_code == 200
    assert matching_entry.json()["data"]["payroll_period_id"] == period.id
    assert mismatched_entry.status_code == 404
    assert response.status_code == 200
    assert [invoice["id"] for invoice in response.json()["data"]] == [own_invoice.id]


@pytest.mark.asyncio
async def test_payroll_requires_manual_resolution_for_legacy_approval_without_snapshot(
    db_session, authenticated_user, record_id_factory
):
    workspace = Workspace(
        id=record_id_factory("workspace"),
        name="Legacy Company",
        slug=record_id_factory("legacy"),
        color="#336699",
        timezone="UTC",
        is_active=True,
    )
    project = Project(
        id=record_id_factory("project"),
        name="Legacy project",
        workspace_id=workspace.id,
        manager_id=authenticated_user.id,
    )
    task_type = TaskType(
        id=record_id_factory("type"),
        name="Previously approved",
        workspace_id=workspace.id,
        unit_rate=Decimal("50.00"),
        unit="per_task",
    )
    task = Task(
        id=record_id_factory("task"),
        project_id=project.id,
        workspace_id=workspace.id,
        task_type_id=task_type.id,
        title="Legacy approval",
        status="done",
    )
    assignment = TaskAssignment(
        id=record_id_factory("assignment"),
        task_id=task.id,
        user_id=authenticated_user.id,
        assigned_by=authenticated_user.id,
        idx=1,
        assigned_at=datetime(2026, 10, 5),
        is_active=False,
        status="completed",
    )
    submission = TaskSubmission(
        id=record_id_factory("submission"),
        task_assignment_id=assignment.id,
        version=1,
        status="approved",
        submitted_by=authenticated_user.id,
        submitted_at=datetime(2026, 10, 8),
    )
    period = PayrollPeriod(
        id=record_id_factory("period"),
        label="Legacy review",
        period_type="bi_monthly",
        start_date=date(2026, 10, 1),
        end_date=date(2026, 10, 14),
        cutoff=date(2026, 10, 14),
        status="open",
    )
    db_session.add_all(
        [
            workspace,
            project,
            task_type,
            task,
            assignment,
            submission,
            period,
            WorkflowLedger(
                entity_type="task",
                record_id=task.id,
                previous_state="approved",
                next_state="done",
                changed_at=datetime(2026, 10, 8, 13),
            ),
        ]
    )
    await db_session.flush()

    with pytest.raises(BadRequestError, match="historical rate"):
        await PayrollService.generate_payroll(
            db_session, authenticated_user, period.id
        )
