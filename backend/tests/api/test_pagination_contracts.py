"""Regression tests for bounded table lists and separate detail endpoints."""

from __future__ import annotations

import pytest

from app.core.framework.models.auth import User
from app.modules.payroll.models import UserTaskRate
from app.modules.project_tasks.models import (
    Project,
    Task,
    TaskAssignment,
    TaskType,
)
from app.modules.utils.models import QrCode, ShortLink
from app.modules.workspaces.models import Workspace


@pytest.mark.asyncio
async def test_admin_users_paginate_filtered_totals(
    authenticated_client,
    authenticated_user,
    db_session,
    record_id_factory,
):
    prefix = record_id_factory("paged-user")
    db_session.add_all(
        User(
            id=record_id_factory("user"),
            username=f"{prefix}-{index}",
            email=f"{prefix}-{index}@example.test",
            full_name=f"Paged User {index}",
            hashed_password="unused",
            is_active=True,
        )
        for index in range(5)
    )
    await db_session.flush()

    page_two = await authenticated_client.get(
        "/api/admin/users",
        params={"search": prefix, "page": 2, "page_size": 2},
    )
    assert page_two.status_code == 200
    payload = page_two.json()["data"]
    assert payload["total"] == 5
    assert payload["page"] == 2
    assert payload["page_size"] == 2
    assert len(payload["users"]) == 2

    last_page = await authenticated_client.get(
        "/api/admin/users",
        params={"search": prefix, "page": 3, "page_size": 2},
    )
    assert last_page.status_code == 200
    assert len(last_page.json()["data"]["users"]) == 1

    out_of_range = await authenticated_client.get(
        "/api/admin/users",
        params={"search": prefix, "page": 4, "page_size": 2},
    )
    assert out_of_range.status_code == 200
    assert out_of_range.json()["data"]["total"] == 5
    assert out_of_range.json()["data"]["users"] == []

    legacy_window = await authenticated_client.get(
        "/api/admin/users",
        params={"search": prefix, "skip": 1, "limit": 1},
    )
    assert legacy_window.status_code == 200
    assert len(legacy_window.json()["data"]["users"]) == 1


@pytest.mark.asyncio
async def test_short_links_paginate_and_keep_detail_endpoint_separate(
    authenticated_client,
    authenticated_user,
    db_session,
    record_id_factory,
):
    prefix = record_id_factory("paged-link")
    links = [
        ShortLink(
            id=record_id_factory("link"),
            slug=f"{prefix}-{index}",
            destination_url=f"https://example.test/{prefix}-{index}",
            title=f"Paged link {index}",
            is_active=True,
            click_count=0,
            created_by=authenticated_user.id,
            last_modified_by=authenticated_user.id,
        )
        for index in range(5)
    ]
    db_session.add_all(links)
    await db_session.flush()

    response = await authenticated_client.get(
        "/api/utils/links",
        params={
            "status": "all",
            "search": prefix,
            "page": 3,
            "page_size": 2,
        },
    )
    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["total"] == 5
    assert payload["page"] == 3
    assert payload["page_size"] == 2
    assert len(payload["data"]) == 1

    detail = await authenticated_client.get(f"/api/utils/links/{links[0].id}")
    assert detail.status_code == 200
    detail_payload = detail.json()["data"]
    assert detail_payload["record"]["id"] == links[0].id
    assert "analytics" in detail_payload


@pytest.mark.asyncio
async def test_qr_codes_paginate_and_keep_detail_endpoint_separate(
    authenticated_client,
    authenticated_user,
    db_session,
    record_id_factory,
):
    records = [
        QrCode(
            id=record_id_factory("qr"),
            source_type="text",
            source_value=f"paged-qr-{index}",
            format="svg",
            created_by=authenticated_user.id,
            last_modified_by=authenticated_user.id,
        )
        for index in range(5)
    ]
    db_session.add_all(records)
    await db_session.flush()

    response = await authenticated_client.get(
        "/api/utils/qr",
        params={"page": 3, "page_size": 2},
    )
    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["total"] == 5
    assert payload["page"] == 3
    assert payload["page_size"] == 2
    assert len(payload["data"]) == 1

    detail = await authenticated_client.get(f"/api/utils/qr/{records[0].id}")
    assert detail.status_code == 200
    detail_payload = detail.json()["data"]
    assert detail_payload["record"]["id"] == records[0].id
    assert detail_payload["data_url"]


@pytest.mark.asyncio
async def test_payroll_task_types_and_rates_paginate_filtered_totals(
    authenticated_client,
    authenticated_user,
    db_session,
    record_id_factory,
):
    prefix = record_id_factory("paged-payroll")
    workspace = Workspace(
        id=record_id_factory("workspace"),
        name=f"{prefix} workspace",
        slug=record_id_factory("workspace-slug").lower(),
        color="#3b82f6",
        timezone="UTC",
        is_active=True,
    )
    db_session.add(workspace)
    await db_session.flush()

    task_types = [
        TaskType(
            id=record_id_factory("task-type"),
            name=f"{prefix} type {index}",
            workspace_id=workspace.id,
            description="Payroll pagination test",
            unit_rate=100 + index,
            unit="hour",
            requires_approval=True,
        )
        for index in range(5)
    ]
    db_session.add_all(task_types)
    await db_session.flush()

    types_response = await authenticated_client.get(
        "/api/payroll/task-types",
        params={"search": prefix, "page": 3, "page_size": 2},
    )
    assert types_response.status_code == 200
    types_payload = types_response.json()
    assert types_payload["total"] == 5
    assert types_payload["page"] == 3
    assert types_payload["page_size"] == 2
    assert len(types_payload["data"]) == 1

    rates = [
        UserTaskRate(
            id=record_id_factory("rate"),
            workspace_id=workspace.id,
            task_type_id=task_types[index].id,
            user_id=authenticated_user.id,
            rate=120 + index,
        )
        for index in range(5)
    ]
    db_session.add_all(rates)
    await db_session.flush()

    rates_response = await authenticated_client.get(
        "/api/payroll/rates",
        params={
            "workspace_id": workspace.id,
            "search": authenticated_user.full_name,
            "page": 2,
            "page_size": 2,
        },
    )
    assert rates_response.status_code == 200
    rates_payload = rates_response.json()
    assert rates_payload["total"] == 5
    assert rates_payload["page"] == 2
    assert len(rates_payload["data"]) == 2


@pytest.mark.asyncio
async def test_my_tasks_paginate_assignments_and_statuses(
    authenticated_client,
    authenticated_user,
    db_session,
    record_id_factory,
):
    prefix = record_id_factory("my-task")
    workspace = Workspace(
        id=record_id_factory("workspace"),
        name=f"{prefix} workspace",
        slug=record_id_factory("workspace-slug").lower(),
        color="#3b82f6",
        timezone="UTC",
        is_active=True,
    )
    project = Project(
        id=record_id_factory("project"),
        workspace_id=workspace.id,
        name=f"{prefix} project",
    )
    db_session.add_all([workspace, project])
    await db_session.flush()

    statuses = ["pending", "in_progress", "submitted", "closed", "approved"]
    tasks = [
        Task(
            id=record_id_factory("task"),
            project_id=project.id,
            workspace_id=workspace.id,
            title=f"{prefix} task {index}",
            status=statuses[index],
        )
        for index in range(5)
    ]
    db_session.add_all(tasks)
    db_session.add_all(
        TaskAssignment(
            id=record_id_factory("assignment"),
            task_id=task.id,
            user_id=authenticated_user.id,
            is_active=True,
        )
        for task in tasks
    )
    await db_session.flush()

    active = await authenticated_client.get(
        "/api/project-tasks/my-tasks",
        params={
            "status": "active",
            "search": prefix,
            "page": 2,
            "page_size": 2,
        },
    )
    assert active.status_code == 200
    active_payload = active.json()
    assert active_payload["total"] == 3
    assert active_payload["page"] == 2
    assert len(active_payload["data"]) == 1
    assert active_payload["data"][0]["status"] in {
        "pending",
        "in_progress",
        "submitted",
    }

    completed = await authenticated_client.get(
        "/api/project-tasks/my-tasks",
        params={"status": "completed", "search": prefix, "page": 1, "page_size": 10},
    )
    assert completed.status_code == 200
    completed_payload = completed.json()
    assert completed_payload["total"] == 2
    assert {row["status"] for row in completed_payload["data"]} == {
        "closed",
        "approved",
    }


@pytest.mark.asyncio
async def test_generic_entity_list_is_bounded_and_detail_loads_record(
    superuser_client,
    db_session,
    record_id_factory,
):
    prefix = record_id_factory("entity-page")
    workspace = Workspace(
        id=record_id_factory("workspace"),
        name=f"{prefix} workspace",
        slug=record_id_factory("workspace-slug").lower(),
        color="#3b82f6",
        timezone="UTC",
        is_active=True,
    )
    db_session.add(workspace)
    await db_session.flush()
    projects = [
        Project(
            id=record_id_factory("project"),
            workspace_id=workspace.id,
            name=f"{prefix} project {index}",
        )
        for index in range(5)
    ]
    db_session.add_all(projects)
    await db_session.flush()

    response = await superuser_client.get(
        "/api/entity/project/list",
        params={
            "filter_field": "name",
            "filter_value": prefix,
            "page": 3,
            "page_size": 2,
            "fields": "all",
        },
        headers={"X-Workspace-ID": workspace.id},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 5
    assert payload["page"] == 3
    assert payload["page_size"] == 2
    assert len(payload["data"]) == 1

    detail = await superuser_client.get(
        f"/api/entity/project/detail/{projects[0].id}",
        headers={"X-Workspace-ID": workspace.id},
    )
    assert detail.status_code == 200
    assert detail.json()["data"]["id"] == projects[0].id
