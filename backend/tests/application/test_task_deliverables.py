"""Deliverable workflow tests: task-type submission modes, the task's single
current link, project-member visibility, and member-safe task summaries.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.application.services.access_control.row_scope_service import RowScopeService
from app.api.app.project_tasks import _build_task_summaries
from app.application.services.documents.naming_service import NamingAppService
from app.core.database import Base
from app.core.exceptions import BadRequestError
from app.core.framework.models.auth import User
from app.infrastructure.database.repositories.entity_repository import EntityRepository
from app.infrastructure.database.repositories.naming_repository import NamingRepository
from app.modules.project_tasks.models import (
    Project,
    ProjectMember,
    Task,
    TaskLink,
    TaskType,
)
from app.modules.project_tasks.services import (
    ProjectTaskService,
    TaskApprovalService,
    TaskSubmissionService,
)
from app.modules.workspaces.models import Workspace, WorkspaceMembership


def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:10]}"


@pytest_asyncio.fixture(autouse=True)
async def _init_db(db_engine, monkeypatch):
    async with db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    monkeypatch.setattr(
        NamingAppService,
        "generate_id",
        AsyncMock(side_effect=lambda *a, **k: f"TEST-{uuid4().hex[:10]}"),
    )
    monkeypatch.setattr(
        NamingRepository,
        "get_next_id",
        AsyncMock(side_effect=lambda *a, **k: f"TEST-{uuid4().hex[:10]}"),
    )
    yield
    async with db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


def _actor(user: User):
    return SimpleNamespace(
        id=user.id,
        username=user.username,
        roles=[],
        role_ids=[],
        is_superuser=False,
    )


async def _setup(db_session, submission_mode="link"):
    """Create workspace, project, task type, an assignee member, and an assigned task."""
    workspace = Workspace(
        id=_unique("workspace"),
        name=_unique("Workspace"),
        slug=_unique("ws"),
        color="#6366f1",
        timezone="UTC",
        is_active=True,
    )
    manager = User(
        id=str(uuid4()),
        username=_unique("manager"),
        email=f"{uuid4().hex[:8]}@example.com",
        full_name="Manager",
        hashed_password="x",
        is_active=True,
    )
    worker = User(
        id=str(uuid4()),
        username=_unique("worker"),
        email=f"{uuid4().hex[:8]}@example.com",
        full_name="Worker",
        hashed_password="x",
        is_active=True,
    )
    db_session.add_all([workspace, manager, worker])
    await db_session.flush()

    project = Project(
        id=_unique("project"),
        workspace_id=workspace.id,
        name=_unique("Project"),
        manager_id=manager.id,
        status="active",
    )
    task_type = TaskType(
        id=_unique("task-type"),
        workspace_id=workspace.id,
        name=_unique("Type"),
        unit="per_task",
        unit_rate=Decimal("10.00"),
        requires_approval=True,
        submission_mode=submission_mode,
    )
    db_session.add_all([project, task_type])
    db_session.add(
        ProjectMember(
            id=str(uuid4()),
            project_id=project.id,
            user_id=worker.id,
            role="member",
            is_active=True,
        )
    )
    await db_session.flush()

    task = await ProjectTaskService.create_task(
        db_session,
        _actor(manager),
        {
            "project_id": project.id,
            "task_type_id": task_type.id,
            "title": _unique("Task"),
        },
    )
    assignment = await ProjectTaskService.assign_task(
        db_session, _actor(manager), task.id, worker.id
    )
    return workspace, project, task_type, task, manager, worker, assignment


@pytest.mark.asyncio
async def test_link_submission_upserts_single_current_task_link(db_session):
    *_, task, manager, worker, assignment = await _setup(db_session)

    first = await TaskSubmissionService.create_submission(
        db_session,
        _actor(worker),
        {
            "task_assignment_id": assignment.id,
            "external_link": "https://example.com/v1",
        },
    )
    assert first.external_link == "https://example.com/v1"

    links = (await db_session.scalars(select(TaskLink))).all()
    assert len(links) == 1
    assert links[0].url == "https://example.com/v1"
    assert links[0].task_id == task.id

    # Revision without a new link keeps the current one.
    await TaskApprovalService.create_approval(
        db_session, _actor(manager), first.id, "needs_revision", remarks="Fix it"
    )
    second = await TaskSubmissionService.create_submission(
        db_session,
        _actor(worker),
        {
            "task_assignment_id": assignment.id,
            "previous_submission_id": first.id,
        },
    )
    assert second.external_link == "https://example.com/v1"
    links = (await db_session.scalars(select(TaskLink))).all()
    assert len(links) == 1

    # Revision with a new link updates the same task link.
    await TaskApprovalService.create_approval(
        db_session, _actor(manager), second.id, "needs_revision", remarks="Again"
    )
    third = await TaskSubmissionService.create_submission(
        db_session,
        _actor(worker),
        {
            "task_assignment_id": assignment.id,
            "previous_submission_id": second.id,
            "external_link": "https://example.com/v3",
        },
    )
    assert third.external_link == "https://example.com/v3"
    links = (await db_session.scalars(select(TaskLink))).all()
    assert len(links) == 1
    assert links[0].url == "https://example.com/v3"


@pytest.mark.asyncio
async def test_submission_mode_validation(db_session):
    *_, task, manager, worker, assignment = await _setup(
        db_session, submission_mode="text"
    )

    with pytest.raises(BadRequestError, match="content"):
        await TaskSubmissionService.create_submission(
            db_session,
            _actor(worker),
            {"task_assignment_id": assignment.id, "external_link": "https://x"},
        )

    submission = await TaskSubmissionService.create_submission(
        db_session,
        _actor(worker),
        {
            "task_assignment_id": assignment.id,
            "content": "Caption draft body",
        },
    )
    assert submission.content == "Caption draft body"
    assert submission.external_link is None

    # Link-mode task types still reject empty submissions.
    *_, task, manager, worker, assignment = await _setup(db_session)
    with pytest.raises(BadRequestError, match="link"):
        await TaskSubmissionService.create_submission(
            db_session,
            _actor(worker),
            {"task_assignment_id": assignment.id},
        )


@pytest.mark.asyncio
async def test_member_sees_task_and_deliverable_summary(db_session):
    workspace, project, task_type, task, manager, worker, assignment = await _setup(
        db_session
    )
    await TaskSubmissionService.create_submission(
        db_session,
        _actor(worker),
        {
            "task_assignment_id": assignment.id,
            "external_link": "https://example.com/v1",
        },
    )

    peer = User(
        id=str(uuid4()),
        username=_unique("peer"),
        email=f"{uuid4().hex[:8]}@example.com",
        full_name="Peer",
        hashed_password="x",
        is_active=True,
    )
    outsider = User(
        id=str(uuid4()),
        username=_unique("outsider"),
        email=f"{uuid4().hex[:8]}@example.com",
        full_name="Outsider",
        hashed_password="x",
        is_active=True,
    )
    db_session.add_all([peer, outsider])
    db_session.add_all(
        [
            WorkspaceMembership(
                id=str(uuid4()),
                workspace_id=workspace.id,
                user_id=peer.id,
                membership_role="member",
                is_home=True,
                is_active=True,
            ),
            WorkspaceMembership(
                id=str(uuid4()),
                workspace_id=workspace.id,
                user_id=outsider.id,
                membership_role="member",
                is_home=True,
                is_active=True,
            ),
            ProjectMember(
                id=str(uuid4()),
                project_id=project.id,
                user_id=peer.id,
                role="member",
                is_active=True,
            ),
        ]
    )
    await db_session.flush()

    class RBAC:
        async def get_row_scope(self, role_ids, entity):
            return ["all"]

    class MetaRegistry:
        @staticmethod
        def get_owner_field(entity):
            return "created_by"

    class WorkflowRepo:
        async def get_workflow(self, entity):
            return None

    scope = RowScopeService(db_session, RBAC(), MetaRegistry(), WorkflowRepo())

    for user_id, expected in ((peer.id, {task.id}), (outsider.id, set())):
        query = await scope.apply_scope_to_query(
            select(Task), Task, "task", user_id, [], [], False
        )
        assert {t.id for t in (await db_session.scalars(query)).all()} == expected

        link_query = await scope.apply_scope_to_query(
            select(TaskLink), TaskLink, "task_link", user_id, [], [], False
        )
        assert (
            len((await db_session.scalars(link_query)).all()) == len(expected)
        )

    summaries = await _build_task_summaries(db_session, [task.id])
    summary = summaries[task.id]
    assert summary["assignee_user_id"] == worker.id
    assert summary["assignee_name"] == "Worker"
    assert summary["deliverable_url"] == "https://example.com/v1"
    assert summary["has_deliverable"] is True
