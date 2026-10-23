"""Comprehensive API tests for the Project & Task real API (Task 2)."""

from __future__ import annotations

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock


@pytest_asyncio.fixture(autouse=True)
async def _create_tables(db_engine):
    """Create and drop tables for every test so the function-scoped SQLite DB is clean."""
    from app.core.database import Base

    async with db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    from sqlalchemy.ext.asyncio import async_sessionmaker
    from app.modules.workspaces.services import WorkspaceService

    async with async_sessionmaker(db_engine, expire_on_commit=False)() as session:
        await WorkspaceService.seed_defaults(session)
    yield
    async with db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def admin_id(superuser_client, db_session):
    """Return the id of the Administrator user created by superuser_client."""
    from uuid import uuid4

    from sqlalchemy import select

    from app.modules.workspaces.models import WorkspaceMembership

    resp = await superuser_client.get(
        "/api/entity/user/list?filter_field=username&filter_value=Administrator"
    )
    payload = resp.json()
    assert payload["status"] == "success"
    assert payload["data"], "Administrator user not found"
    user_id = payload["data"][0]["id"]
    membership = await db_session.scalar(
        select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == "workspace-oc-music-school",
            WorkspaceMembership.user_id == user_id,
        )
    )
    if not membership:
        db_session.add(
            WorkspaceMembership(
                id=str(uuid4()),
                workspace_id="workspace-oc-music-school",
                user_id=user_id,
                membership_role="supervisor",
                is_home=True,
                is_active=True,
            )
        )
        await db_session.flush()
    return user_id


@pytest.mark.asyncio
async def test_project_generic_crud(superuser_client, admin_id, record_id_factory):
    """Exercise create, list, detail, update and delete for the project entity."""
    name = f"Project-{record_id_factory('proj')}"

    create_resp = await superuser_client.post(
        "/api/entity/project",
        json={
            "data": {
                "name": name,
                "manager_id": admin_id,
                "status": "active",
                "start_date": "2026-07-01",
                "end_date": "2026-07-31",
            },
        },
    )
    assert create_resp.status_code == 201
    create_payload = create_resp.json()
    assert create_payload["status"] == "success"
    project_id = create_payload["data"]["id"]

    list_resp = await superuser_client.get(
        f"/api/entity/project/list?filter_field=name&filter_value={name}"
    )
    list_payload = list_resp.json()
    assert list_payload["status"] == "success"
    assert list_payload["total"] == 1
    assert list_payload["data"][0]["name"] == name

    detail_resp = await superuser_client.get(f"/api/entity/project/detail/{project_id}")
    assert detail_resp.json()["data"]["manager_id"] == admin_id

    new_name = f"Updated-{name}"
    update_resp = await superuser_client.put(
        f"/api/entity/project/{project_id}",
        json={"data": {"name": new_name}},
    )
    assert update_resp.json()["status"] == "success"

    delete_resp = await superuser_client.delete(f"/api/entity/project/{project_id}")
    assert delete_resp.json()["status"] == "success"


@pytest.mark.asyncio
async def test_task_type_generic_crud(superuser_client, record_id_factory):
    """Exercise create, detail and delete for the task_type entity."""
    name = f"TaskType-{record_id_factory('tt')}"
    create_resp = await superuser_client.post(
        "/api/entity/task_type",
        json={
            "data": {
                "name": name,
                "unit_rate": 100.0,
                "unit": "per_task",
                "requires_approval": True,
            },
        },
    )
    assert create_resp.status_code == 201
    payload = create_resp.json()
    assert payload["status"] == "success"
    task_type_id = payload["data"]["id"]

    detail_resp = await superuser_client.get(f"/api/entity/task_type/detail/{task_type_id}")
    assert detail_resp.json()["data"]["name"] == name

    delete_resp = await superuser_client.delete(f"/api/entity/task_type/{task_type_id}")
    assert delete_resp.json()["status"] == "success"


@pytest.mark.asyncio
async def test_create_task_via_project_tasks_endpoint(
    superuser_client, admin_id, record_id_factory
):
    """Assert /api/project-tasks/tasks creates a task and generates audit side effects."""
    project_name = f"Project-{record_id_factory('proj')}"
    project_resp = await superuser_client.post(
        "/api/entity/project",
        json={
            "data": {"name": project_name, "manager_id": admin_id, "status": "active"},
        },
    )
    project_id = project_resp.json()["data"]["id"]

    task_type_name = f"TaskType-{record_id_factory('tt')}"
    task_type_resp = await superuser_client.post(
        "/api/entity/task_type",
        json={
            "data": {
                "name": task_type_name,
                "unit_rate": 75.0,
                "unit": "per_hour",
                "requires_approval": True,
            },
        },
    )
    task_type_id = task_type_resp.json()["data"]["id"]

    title = f"Task-{record_id_factory('task')}"
    create_resp = await superuser_client.post(
        "/api/project-tasks/tasks",
        json={
            "project_id": project_id,
            "task_type_id": task_type_id,
            "workspace_id": "workspace-bahandi",
            "title": title,
            "description": "A test task",
            "priority": "high",
            "status": "pending",
            "due_date": "2026-07-25T10:00:00Z",
        },
    )
    assert create_resp.status_code == 200
    payload = create_resp.json()
    assert payload["status"] == "success"
    task_id = payload["data"]["id"]
    assert payload["data"]["title"] == title
    assert payload["data"]["status"] == "pending"
    assert payload["data"]["priority"] == "high"
    assert payload["data"]["workspace_id"] == "workspace-oc-music-school"

    detail_resp = await superuser_client.get(f"/api/entity/task/detail/{task_id}")
    assert detail_resp.json()["data"]["title"] == title

    list_resp = await superuser_client.get(
        f"/api/entity/task/list?filter_field=project_id&filter_value={project_id}"
    )
    assert list_resp.json()["total"] == 1
    assert list_resp.json()["data"][0]["id"] == task_id

    delete_resp = await superuser_client.delete(f"/api/entity/task/{task_id}")
    assert delete_resp.json()["status"] == "success"


@pytest.mark.asyncio
async def test_assign_task_and_list_assignments(
    superuser_client, admin_id, record_id_factory, monkeypatch
):
    """Assert /api/project-tasks/tasks/{id}/assign creates an active assignment."""
    from app.api.app import project_tasks as project_tasks_api

    email_task = AsyncMock()
    monkeypatch.setattr(
        project_tasks_api, "send_task_assignment_email", email_task
    )

    project_resp = await superuser_client.post(
        "/api/entity/project",
        json={
            "data": {"name": f"Project-{record_id_factory('proj')}", "manager_id": admin_id},
        },
    )
    project_id = project_resp.json()["data"]["id"]

    task_type_resp = await superuser_client.post(
        "/api/entity/task_type",
        json={
            "data": {
                "name": f"TaskType-{record_id_factory('tt')}",
                "unit_rate": 50.0,
                "unit": "per_task",
                "requires_approval": True,
            },
        },
    )
    task_type_id = task_type_resp.json()["data"]["id"]

    task_resp = await superuser_client.post(
        "/api/project-tasks/tasks",
        json={
            "project_id": project_id,
            "task_type_id": task_type_id,
            "title": f"Task-{record_id_factory('task')}",
            "priority": "medium",
            "status": "pending",
        },
    )
    task_id = task_resp.json()["data"]["id"]

    await superuser_client.post(
        "/api/entity/project_member",
        json={"data": {"project_id": project_id, "user_id": admin_id}},
    )
    assign_resp = await superuser_client.post(
        f"/api/project-tasks/tasks/{task_id}/assign",
        json={"user_id": admin_id},
    )
    assert assign_resp.status_code == 200
    assert assign_resp.json()["status"] == "success"
    assert assign_resp.json()["data"]["user_id"] == admin_id
    assert assign_resp.json()["data"]["is_active"] is True

    assignments_resp = await superuser_client.get(
        f"/api/project-tasks/tasks/{task_id}/assignments"
    )
    assert assignments_resp.json()["status"] == "success"
    assignments = assignments_resp.json()["data"]["data"]
    assert len(assignments) == 1
    assert assignments[0]["user_id"] == admin_id

    task_detail = await superuser_client.get(f"/api/entity/task/detail/{task_id}")
    assert task_detail.json()["data"]["status"] == "in_progress"
    email_task.assert_awaited_once_with(task_id, admin_id)


@pytest.mark.asyncio
async def test_task_status_update(
    superuser_client, admin_id, record_id_factory, db_session
):
    """Assert task status changes use an authorized workflow transition."""
    from app.core.seeds.workflows import seed_workflows

    await seed_workflows(db_session)
    project_resp = await superuser_client.post(
        "/api/entity/project",
        json={
            "data": {"name": f"Project-{record_id_factory('proj')}", "manager_id": admin_id},
        },
    )
    project_id = project_resp.json()["data"]["id"]

    task_type_resp = await superuser_client.post(
        "/api/entity/task_type",
        json={
            "data": {
                "name": f"TaskType-{record_id_factory('tt')}",
                "unit_rate": 50.0,
                "unit": "per_task",
            },
        },
    )
    task_type_id = task_type_resp.json()["data"]["id"]

    task_resp = await superuser_client.post(
        "/api/project-tasks/tasks",
        json={
            "project_id": project_id,
            "task_type_id": task_type_id,
            "title": f"Task-{record_id_factory('task')}",
            "status": "pending",
        },
    )
    task_id = task_resp.json()["data"]["id"]

    update_resp = await superuser_client.put(
        f"/api/entity/task/{task_id}",
        json={"data": {"status": "in_progress"}},
    )
    assert update_resp.json()["status"] == "error"

    workflow_resp = await superuser_client.post(
        "/api/entity/task/workflow",
        json={"id": task_id, "action": "start"},
    )
    assert workflow_resp.json()["status"] == "success"

    detail_resp = await superuser_client.get(f"/api/entity/task/detail/{task_id}")
    assert detail_resp.json()["data"]["status"] == "pending"

    lifecycle_resp = await superuser_client.post(
        "/api/entity/task/workflow",
        json={"id": task_id, "action": "submit_for_review"},
    )
    assert lifecycle_resp.json()["status"] == "error"
    assert "submission/review endpoints" in lifecycle_resp.json()["message"]


@pytest.mark.asyncio
async def test_task_list_filters_by_project(superuser_client, admin_id, record_id_factory):
    """Assert the task list can be filtered by project_id."""
    project_a = await superuser_client.post(
        "/api/entity/project",
        json={
            "data": {"name": f"Project-A-{record_id_factory('proj')}", "manager_id": admin_id},
        },
    )
    project_b = await superuser_client.post(
        "/api/entity/project",
        json={
            "data": {"name": f"Project-B-{record_id_factory('proj')}", "manager_id": admin_id},
        },
    )
    task_type = await superuser_client.post(
        "/api/entity/task_type",
        json={
            "data": {
                "name": f"TaskType-{record_id_factory('tt')}",
                "unit_rate": 1.0,
                "unit": "per_unit",
            },
        },
    )
    tt_id = task_type.json()["data"]["id"]

    await superuser_client.post(
        "/api/project-tasks/tasks",
        json={
            "project_id": project_a.json()["data"]["id"],
            "task_type_id": tt_id,
            "title": f"Task-{record_id_factory('task')}",
        },
    )
    await superuser_client.post(
        "/api/project-tasks/tasks",
        json={
            "project_id": project_b.json()["data"]["id"],
            "task_type_id": tt_id,
            "title": f"Task-{record_id_factory('task')}",
        },
    )

    list_a = await superuser_client.get(
        f"/api/entity/task/list?filter_field=project_id&filter_value={project_a.json()['data']['id']}"
    )
    assert list_a.json()["total"] == 1
    assert list_a.json()["data"][0]["project_id"] == project_a.json()["data"]["id"]


@pytest.mark.asyncio
async def test_project_color_and_icon(superuser_client, admin_id, record_id_factory):
    """Assert the new project color and icon fields are stored and returned."""
    name = f"Project-{record_id_factory('proj')}"
    create_resp = await superuser_client.post(
        "/api/entity/project",
        json={
            "data": {
                "name": name,
                "manager_id": admin_id,
                "color": "#ef4444",
                "icon": "rocket",
            },
        },
    )
    project_id = create_resp.json()["data"]["id"]

    detail_resp = await superuser_client.get(f"/api/entity/project/detail/{project_id}")
    data = detail_resp.json()["data"]
    assert data["color"] == "#ef4444"
    assert data["icon"] == "rocket"


@pytest.mark.asyncio
async def test_task_category_and_link(superuser_client, admin_id, record_id_factory):
    """Assert task_category and task_link entities work end-to-end and link to task."""
    category_name = f"Category-{record_id_factory('cat')}"
    category_resp = await superuser_client.post(
        "/api/entity/task_category",
        json={
            "data": {
                "name": category_name,
                "color": "#10b981",
                "icon": "video",
            },
        },
    )
    category_id = category_resp.json()["data"]["id"]

    project_resp = await superuser_client.post(
        "/api/entity/project",
        json={
            "data": {"name": f"Project-{record_id_factory('proj')}", "manager_id": admin_id},
        },
    )
    project_id = project_resp.json()["data"]["id"]

    task_type_resp = await superuser_client.post(
        "/api/entity/task_type",
        json={
            "data": {
                "name": f"TaskType-{record_id_factory('tt')}",
                "unit_rate": 10.0,
                "unit": "per_task",
            },
        },
    )
    task_type_id = task_type_resp.json()["data"]["id"]

    task_resp = await superuser_client.post(
        "/api/entity/task",
        json={
            "data": {
                "project_id": project_id,
                "task_type_id": task_type_id,
                "category_id": category_id,
                "title": f"Task-{record_id_factory('task')}",
                "priority": "medium",
                "status": "pending",
            },
        },
    )
    task_id = task_resp.json()["data"]["id"]

    detail_resp = await superuser_client.get(f"/api/entity/task/detail/{task_id}")
    assert detail_resp.json()["data"]["category_id"] == category_id

    link_resp = await superuser_client.post(
        "/api/entity/task_link",
        json={
            "data": {
                "task_id": task_id,
                "url": "https://example.com/asset",
                "label": "Asset",
            },
        },
    )
    assert link_resp.json()["status"] == "success"
    link_id = link_resp.json()["data"]["id"]

    list_resp = await superuser_client.get(
        f"/api/entity/task_link/list?filter_field=task_id&filter_value={task_id}"
    )
    assert list_resp.json()["total"] == 1
    assert list_resp.json()["data"][0]["id"] == link_id


@pytest.mark.asyncio
async def test_member_lists_home_and_cross_project_records_only(client, db_session):
    from datetime import datetime, timedelta, timezone
    from uuid import uuid4

    from jose import jwt

    from app.core.config import settings
    from app.core.framework.models.auth import User
    from app.modules.project_tasks.models import (
        Project,
        ProjectMember,
        Task,
        TaskAssignment,
    )
    from app.modules.workspaces.models import WorkspaceMembership

    member = User(
        id=str(uuid4()),
        username="workspace-member",
        email="workspace-member@example.test",
        full_name="Workspace Member",
        hashed_password="unused",
        is_active=True,
    )
    home_project = Project(
        id="scope-home-project",
        workspace_id="workspace-fourth-street",
        name="Home project",
        status="active",
    )
    cross_project = Project(
        id="scope-cross-project",
        workspace_id="workspace-bahandi",
        name="Cross-company project",
        status="active",
    )
    private_project = Project(
        id="scope-private-project",
        workspace_id="workspace-bahandi",
        name="Private project",
        status="active",
    )
    legacy_project = Project(
        id="scope-legacy-project",
        name="Unmapped project",
        status="active",
    )
    db_session.add_all([member, home_project, cross_project, private_project, legacy_project])
    await db_session.flush()
    db_session.add_all(
        [
            WorkspaceMembership(
                id=str(uuid4()),
                workspace_id="workspace-fourth-street",
                user_id=member.id,
                membership_role="member",
                is_home=True,
                is_active=True,
            ),
            ProjectMember(
                id=str(uuid4()),
                project_id=cross_project.id,
                user_id=member.id,
                role="member",
                is_active=True,
            ),
            Task(
                id="scope-home-task",
                project_id=home_project.id,
                workspace_id=home_project.workspace_id,
                title="Home task",
            ),
            Task(
                id="scope-cross-task",
                project_id=cross_project.id,
                workspace_id=cross_project.workspace_id,
                title="Cross task",
            ),
            Task(
                id="scope-private-task",
                project_id=private_project.id,
                workspace_id=private_project.workspace_id,
                title="Private task",
            ),
            Task(id="scope-legacy-task", project_id=legacy_project.id, title="Unmapped task"),
            TaskAssignment(
                id="scope-cross-assignment",
                task_id="scope-cross-task",
                user_id=member.id,
                is_active=True,
                status="active",
            ),
        ]
    )
    await db_session.commit()

    token = jwt.encode(
        {
            "sub": member.username,
            "user_id": member.id,
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    headers = {"Authorization": f"Bearer {token}"}

    projects_response = await client.get("/api/entity/project/list", headers=headers)
    assert projects_response.status_code == 200
    assert {row["id"] for row in projects_response.json()["data"]} == {
        cross_project.id,
    }

    tasks_response = await client.get("/api/entity/task/list", headers=headers)
    assert tasks_response.status_code == 200
    assert {row["id"] for row in tasks_response.json()["data"]} == {
        "scope-cross-task",
    }

    private_detail = await client.get(
        f"/api/entity/project/detail/{private_project.id}", headers=headers
    )
    assert private_detail.status_code == 403


@pytest.mark.asyncio
async def test_workspace_admin_assigns_scoped_memberships_and_maps_legacy_project(
    superuser_client, db_session
):
    from uuid import uuid4

    from app.core.framework.models.auth import User
    from app.modules.project_tasks.models import Project

    user = User(
        id=str(uuid4()),
        username="multi-workspace-supervisor",
        email="multi-workspace-supervisor@example.test",
        full_name="Multi Workspace Supervisor",
        hashed_password="unused",
        is_active=True,
    )
    legacy_project = Project(
        id="legacy-unmapped-project",
        name="Legacy project",
        status="active",
    )
    db_session.add_all([user, legacy_project])
    await db_session.commit()

    home_membership = await superuser_client.post(
        "/api/workspaces/workspace-fourth-street/memberships",
        json={
            "user_id": user.id,
            "membership_role": "supervisor",
            "is_home": True,
        },
    )
    additional_membership = await superuser_client.post(
        "/api/workspaces/workspace-bahandi/memberships",
        json={
            "user_id": user.id,
            "membership_role": "supervisor",
            "is_home": False,
        },
    )
    assert home_membership.status_code == 200
    assert additional_membership.status_code == 200

    mapping = await superuser_client.post(
        "/api/workspaces/map-legacy",
        json={
            "entity": "project",
            "record_id": legacy_project.id,
            "workspace_id": "workspace-bahandi",
        },
    )
    assert mapping.status_code == 200
    await db_session.refresh(legacy_project)
    assert legacy_project.workspace_id == "workspace-bahandi"

    context_response = await superuser_client.get(
        "/api/workspaces/context", headers={"X-Workspace-ID": ""}
    )
    assert context_response.status_code == 200
    context_data = context_response.json()["data"]
    assert context_data["is_global"] is True
    assert context_data["capabilities"]["can_view_all_workspaces"] is True
    assert context_data["capabilities"]["can_manage_payroll"] is True
    assert all(
        workspace["can_manage"] for workspace in context_data["workspaces"]
    )


@pytest.mark.asyncio
async def test_project_member_candidates_support_cross_workspace_users(
    client, db_session, monkeypatch
):
    from datetime import datetime, timedelta, timezone
    from uuid import uuid4

    from jose import jwt
    from sqlalchemy import select

    from app.core.config import settings
    from app.core.framework.models.auth import User
    from app.modules.project_tasks.models import Project, ProjectMember, Task, TaskType
    from app.modules.workspaces.models import WorkspaceMembership

    supervisor = User(
        id=str(uuid4()),
        username="candidate-supervisor",
        email="candidate-supervisor@example.test",
        full_name="Candidate Supervisor",
        hashed_password="unused",
        is_active=True,
    )
    collaborator = User(
        id=str(uuid4()),
        username="external-collaborator",
        email="external-collaborator@example.test",
        full_name="External Collaborator",
        hashed_password="unused",
        is_active=True,
    )
    outside_supervisor = User(
        id=str(uuid4()),
        username="outside-supervisor",
        email="outside-supervisor@example.test",
        full_name="Outside Supervisor",
        hashed_password="unused",
        is_active=True,
    )
    inactive_user = User(
        id=str(uuid4()),
        username="inactive-collaborator",
        email="inactive-collaborator@example.test",
        full_name="Inactive Collaborator",
        hashed_password="unused",
        is_active=False,
    )
    regular_member = User(
        id=str(uuid4()),
        username="regular-member",
        email="regular-member@example.test",
        full_name="Regular Member",
        hashed_password="unused",
        is_active=True,
    )
    project = Project(
        id=f"project-{uuid4().hex[:12]}",
        workspace_id="workspace-oc-music-school",
        name="Cross-workspace project",
        status="active",
    )
    db_session.add_all(
        [
            supervisor,
            collaborator,
            outside_supervisor,
            inactive_user,
            regular_member,
            project,
        ]
    )
    await db_session.flush()
    db_session.add_all(
        [
            WorkspaceMembership(
                id=str(uuid4()),
                workspace_id="workspace-oc-music-school",
                user_id=supervisor.id,
                membership_role="supervisor",
                is_home=True,
                is_active=True,
            ),
            WorkspaceMembership(
                id=str(uuid4()),
                workspace_id="workspace-bahandi",
                user_id=outside_supervisor.id,
                membership_role="supervisor",
                is_home=True,
                is_active=True,
            ),
            WorkspaceMembership(
                id=str(uuid4()),
                workspace_id="workspace-bahandi",
                user_id=inactive_user.id,
                membership_role="member",
                is_home=True,
                is_active=True,
            ),
            WorkspaceMembership(
                id=str(uuid4()),
                workspace_id="workspace-oc-music-school",
                user_id=regular_member.id,
                membership_role="member",
                is_home=True,
                is_active=True,
            ),
        ]
    )
    await db_session.commit()

    def auth_headers(user: User, workspace_id: str) -> dict[str, str]:
        token = jwt.encode(
            {
                "sub": user.username,
                "user_id": user.id,
                "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
            },
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM,
        )
        return {
            "Authorization": f"Bearer {token}",
            "X-Workspace-ID": workspace_id,
        }

    response = await client.get(
        f"/api/project-tasks/projects/{project.id}/member-candidates",
        headers=auth_headers(supervisor, project.workspace_id),
    )
    assert response.status_code == 200
    candidates = {row["id"]: row for row in response.json()["data"]}
    assert collaborator.id in candidates
    assert inactive_user.id not in candidates
    assert candidates[collaborator.id]["memberships"] == []
    assert {
        membership["workspace_name"]
        for membership in candidates[outside_supervisor.id]["memberships"]
    } == {"Bahandi Entertainment"}
    db_session.add_all(
        [
            ProjectMember(
                id=str(uuid4()),
                project_id=project.id,
                user_id=regular_member.id,
                role="member",
                is_active=True,
            ),
            ProjectMember(
                id=str(uuid4()),
                project_id=project.id,
                user_id=outside_supervisor.id,
                role="member",
                is_active=False,
            ),
        ]
    )
    await db_session.flush()
    directory = await client.get(
        "/api/workspaces/directory",
        params={
            "search": "Regular",
            "project_id": project.id,
            "page": 1,
            "page_size": 1,
        },
        headers=auth_headers(supervisor, project.workspace_id),
    )
    assert directory.status_code == 200
    assert [user["id"] for user in directory.json()["data"]] == [
        regular_member.id
    ]
    assert directory.json()["total"] == 1

    denied = await client.get(
        f"/api/project-tasks/projects/{project.id}/member-candidates",
        headers=auth_headers(regular_member, project.workspace_id),
    )
    assert denied.status_code == 403

    create_member = await client.post(
        "/api/entity/project_member",
        json={
            "data": {
                "project_id": project.id,
                "user_id": collaborator.id,
                "role": "manager",
            }
        },
        headers=auth_headers(supervisor, project.workspace_id),
    )
    assert create_member.status_code in {200, 201}
    membership = await db_session.scalar(
        select(ProjectMember).where(
            ProjectMember.project_id == project.id,
            ProjectMember.user_id == collaborator.id,
        )
    )
    assert membership is not None
    assert membership.role == "manager"

    db_session.add(
        ProjectMember(
            id=str(uuid4()),
            project_id=project.id,
            user_id=regular_member.id,
            role="member",
            is_active=True,
        )
    )
    task_type = TaskType(
        id=f"task-type-{uuid4().hex[:12]}",
        workspace_id=project.workspace_id,
        name="Cross-workspace assignment",
        unit="per_task",
        unit_rate=50,
        requires_approval=True,
    )
    task = Task(
        id=f"task-{uuid4().hex[:12]}",
        project_id=project.id,
        workspace_id=project.workspace_id,
        task_type_id=task_type.id,
        title="Assigned to workspace-free user",
        status="pending",
    )
    db_session.add_all([task_type, task])
    await db_session.flush()

    from app.api.app import project_tasks as project_tasks_api

    assignment_email = AsyncMock()
    monkeypatch.setattr(
        project_tasks_api, "send_task_assignment_email", assignment_email
    )
    assignment = await client.post(
        f"/api/project-tasks/tasks/{task.id}/assign",
        json={"user_id": regular_member.id},
        headers=auth_headers(collaborator, project.workspace_id),
    )
    assert assignment.status_code == 200
    assert assignment.json()["data"]["user_id"] == regular_member.id
    assignment_email.assert_awaited_once_with(task.id, regular_member.id)

    project_directory = await client.get(
        "/api/workspaces/directory",
        params={"project_id": project.id, "search": "External"},
        headers=auth_headers(collaborator, project.workspace_id),
    )
    assert project_directory.status_code == 200
    assert [user["id"] for user in project_directory.json()["data"]] == [
        collaborator.id
    ]
