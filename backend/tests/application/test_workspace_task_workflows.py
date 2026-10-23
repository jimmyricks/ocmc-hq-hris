from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select

from app.application.services.documents.naming_service import NamingAppService
from app.core.database import Base
from app.core.framework.models.auth import User
from app.core.framework.models.workflow import Workflow
from app.core.seeds.workflows import seed_workflows
from app.infrastructure.database.repositories.naming_repository import NamingRepository
from app.infrastructure.database.repositories.workflow_repository import WorkflowRepository
from app.modules.project_tasks.models import (
    Project,
    ProjectMember,
    Task,
    TaskAssignment,
    TaskType,
)
from app.modules.project_tasks.services import (
    ProjectTaskService,
    TaskApprovalService,
    TaskSubmissionService,
    _apply_task_workflow_transition,
)
from app.modules.workspaces.models import Workspace, WorkspaceMembership
from app.modules.workspaces.services import WorkspaceService

WORKSPACE_ID = "workspace-oc-music-school"


@pytest_asyncio.fixture(autouse=True)
async def workflow_schema(db_engine, monkeypatch):
    async with db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    monkeypatch.setattr(
        NamingAppService,
        "generate_id",
        AsyncMock(side_effect=lambda *args, **kwargs: f"TEST-{uuid4().hex[:10]}"),
    )
    monkeypatch.setattr(
        NamingRepository,
        "get_next_id",
        AsyncMock(side_effect=lambda *args, **kwargs: f"TEST-{uuid4().hex[:10]}"),
    )
    yield

    async with db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def seeded_workspace(db_session):
    await WorkspaceService.seed_defaults(db_session)
    result = await seed_workflows(db_session)
    workspace = await db_session.get(Workspace, WORKSPACE_ID)
    return workspace, result


def actor(user: User):
    return SimpleNamespace(
        id=user.id,
        username=user.username,
        roles=[],
        role_ids=[],
        is_superuser=False,
    )


async def make_user(db_session, role: str, prefix: str) -> User:
    user = User(
        id=str(uuid4()),
        username=f"{prefix}-{uuid4().hex[:8]}",
        email=f"{prefix}-{uuid4().hex[:8]}@example.com",
        full_name=f"{prefix.title()} User",
        hashed_password="not-used",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    db_session.add(
        WorkspaceMembership(
            id=str(uuid4()),
            workspace_id=WORKSPACE_ID,
            user_id=user.id,
            membership_role=role,
            is_home=True,
            is_active=True,
        )
    )
    await db_session.flush()
    return user


async def make_external_user(db_session, prefix: str) -> User:
    user = User(
        id=str(uuid4()),
        username=f"{prefix}-{uuid4().hex[:8]}",
        email=f"{prefix}-{uuid4().hex[:8]}@example.com",
        full_name=f"{prefix.title()} User",
        hashed_password="not-used",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def make_project(db_session, manager: User):
    project = Project(
        id=f"project-{uuid4().hex[:12]}",
        workspace_id=WORKSPACE_ID,
        name="Workflow Project",
        manager_id=manager.id,
        status="active",
        created_by=manager.id,
        last_modified_by=manager.id,
    )
    task_type = TaskType(
        id=f"task-type-{uuid4().hex[:12]}",
        workspace_id=WORKSPACE_ID,
        name="Deliverable",
        unit="per_task",
        unit_rate=100,
        requires_approval=True,
        created_by=manager.id,
        last_modified_by=manager.id,
    )
    db_session.add_all([project, task_type])
    await db_session.flush()
    return project, task_type


async def make_project_member(db_session, project: Project, user: User):
    membership = ProjectMember(
        id=str(uuid4()),
        project_id=project.id,
        user_id=user.id,
        role="member",
        is_active=True,
        created_by=user.id,
        last_modified_by=user.id,
    )
    db_session.add(membership)
    await db_session.flush()
    return membership


@pytest.mark.asyncio
async def test_default_task_workflow_is_seeded_per_workspace(seeded_workspace, db_session):
    workspace, result = seeded_workspace
    assert result.created > 0

    repository = WorkflowRepository(db_session)
    workflow = await repository.get_workflow("task", workspace_id=workspace.id)
    assert workflow is not None
    assert workflow.is_default is True
    assert workflow.name == "Standard Task Lifecycle"
    assert await repository.get_initial_state("task", workspace.id) == "draft"

    states = {link.state.slug for link in workflow.state_links}
    assert {
        "draft",
        "pending",
        "for_approval",
        "approved",
        "needs_revision",
        "done",
    }.issubset(states)

    second_result = await seed_workflows(db_session)
    assert second_result.created == 0
    assert second_result.skipped > 0


@pytest.mark.asyncio
async def test_workspace_default_workflow_selection(seeded_workspace, db_session):
    workspace, _ = seeded_workspace
    repository = WorkflowRepository(db_session)
    seeded = await repository.get_workflow("task", workspace_id=workspace.id)
    assert seeded is not None

    custom = Workflow(
        name="Custom Task Lifecycle",
        target_entity="task",
        workspace_id=workspace.id,
        is_active=True,
        is_default=False,
    )
    db_session.add(custom)
    await db_session.flush()
    assert (await repository.get_workflow("task", workspace.id)).id == seeded.id

    seeded.is_default = False
    await db_session.flush()
    custom.is_default = True
    await db_session.flush()
    assert (await repository.get_workflow("task", workspace.id)).id == custom.id

    custom.is_active = False
    custom.is_default = False
    await db_session.flush()
    seeded.is_default = True
    await db_session.flush()
    assert (await repository.get_workflow("task", workspace.id)).id == seeded.id


@pytest.mark.asyncio
async def test_member_and_supervisor_transition_permissions(seeded_workspace, db_session):
    member = await make_external_user(db_session, "member")
    supervisor = await make_user(db_session, "supervisor", "supervisor")
    project = Project(
        id=f"project-{uuid4().hex[:12]}",
        workspace_id=WORKSPACE_ID,
        name="Transition Project",
    )
    db_session.add(project)
    await db_session.flush()
    await make_project_member(db_session, project, member)
    task = SimpleNamespace(
        id=f"task-{uuid4().hex[:8]}",
        project_id=project.id,
        workspace_id=WORKSPACE_ID,
        created_by=member.id,
    )
    repository = WorkflowRepository(db_session)

    member_start = await repository.get_available_actions(
        "task", "draft", actor(member), task.id, doc=task
    )
    supervisor_start = await repository.get_available_actions(
        "task", "draft", actor(supervisor), task.id, doc=task
    )
    assert {item["action_slug"] for item in member_start} == {"start"}
    assert {item["action_slug"] for item in supervisor_start} == {"start"}

    member_pending = await repository.get_available_actions(
        "task", "pending", actor(member), task.id, doc=task
    )
    supervisor_pending = await repository.get_available_actions(
        "task", "pending", actor(supervisor), task.id, doc=task
    )
    assert {item["action_slug"] for item in member_pending} == {"submit_for_review"}
    assert supervisor_pending == []

    member_review = await repository.get_available_actions(
        "task", "for_approval", actor(member), task.id, doc=task
    )
    supervisor_review = await repository.get_available_actions(
        "task", "for_approval", actor(supervisor), task.id, doc=task
    )
    assert member_review == []
    assert {item["action_slug"] for item in supervisor_review} == {
        "approve",
        "request_changes",
        "reject",
    }

    valid, _, error = await repository.validate_transition(
        "task", "for_approval", "approve", actor(member), task.id, doc=task
    )
    assert valid is False
    assert "permission" in error.lower()


@pytest.mark.asyncio
async def test_task_lifecycle_uses_workspace_workflow(
    seeded_workspace, db_session
):
    member = await make_user(db_session, "member", "member")
    supervisor = await make_user(db_session, "supervisor", "supervisor")
    project, task_type = await make_project(db_session, supervisor)
    await make_project_member(db_session, project, member)

    task = await ProjectTaskService.create_task(
        db_session,
        actor(supervisor),
        {
            "project_id": project.id,
            "task_type_id": task_type.id,
            "title": "Workspace workflow task",
        },
    )
    assert task.status == "draft"
    assert task.workspace_id == WORKSPACE_ID

    assignment = await ProjectTaskService.assign_task(
        db_session, actor(supervisor), task.id, member.id
    )
    assert assignment.is_active is True
    await db_session.refresh(task)
    assert task.status == "draft"

    repository = WorkflowRepository(db_session)
    start, error = await repository.find_transition(
        "task", task.status, "start", actor(member), task.id, doc=task
    )
    assert error is None
    await _apply_task_workflow_transition(db_session, actor(member), task, start)
    assert task.status == "pending"

    submission = await TaskSubmissionService.create_submission(
        db_session,
        actor(member),
        {"task_assignment_id": assignment.id, "external_link": "https://example.com/deliverable", "notes": "Ready"},
    )
    assert submission.status == "submitted"
    await db_session.refresh(task)
    assert task.status == "for_approval"

    with pytest.raises(Exception, match="permission"):
        await TaskApprovalService.create_approval(
            db_session, actor(member), submission.id, "approved"
        )

    approval = await TaskApprovalService.create_approval(
        db_session, actor(supervisor), submission.id, "approved"
    )
    assert approval.decision == "approved"
    await db_session.refresh(task)
    assert task.status == "approved"
    assert submission.approved_amount == 100

    complete, error = await repository.find_transition(
        "task", task.status, "complete", actor(supervisor), task.id, doc=task
    )
    assert error is None
    await _apply_task_workflow_transition(db_session, actor(supervisor), task, complete)
    assert task.status == "done"


@pytest.mark.asyncio
async def test_cross_workspace_project_members_can_work_and_review(
    seeded_workspace, db_session
):
    worker = await make_external_user(db_session, "external-worker")
    reviewer = await make_external_user(db_session, "external-reviewer")
    supervisor = await make_user(db_session, "supervisor", "supervisor")
    project, task_type = await make_project(db_session, supervisor)
    await make_project_member(db_session, project, worker)
    db_session.add(
        ProjectMember(
            id=str(uuid4()),
            project_id=project.id,
            user_id=reviewer.id,
            role="manager",
            is_active=True,
            created_by=supervisor.id,
            last_modified_by=supervisor.id,
        )
    )
    await db_session.flush()

    task = await ProjectTaskService.create_task(
        db_session,
        actor(supervisor),
        {
            "project_id": project.id,
            "task_type_id": task_type.id,
            "title": "Cross-workspace task",
        },
    )
    assignment = await ProjectTaskService.assign_task(
        db_session, actor(supervisor), task.id, worker.id
    )

    repository = WorkflowRepository(db_session)
    start, error = await repository.find_transition(
        "task", task.status, "start", actor(worker), task.id, doc=task
    )
    assert error is None
    await _apply_task_workflow_transition(db_session, actor(worker), task, start)

    submission = await TaskSubmissionService.create_submission(
        db_session,
        actor(worker),
        {"task_assignment_id": assignment.id, "external_link": "https://example.com/deliverable", "notes": "Cross-workspace work"},
    )
    await db_session.refresh(task)
    assert task.status == "for_approval"

    approval = await TaskApprovalService.create_approval(
        db_session, actor(reviewer), submission.id, "approved"
    )
    assert approval.decision == "approved"
    await db_session.refresh(task)
    assert task.status == "approved"
