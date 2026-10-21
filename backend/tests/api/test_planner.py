from datetime import date, datetime
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.database import Base
from app.modules.project_tasks.models import Project, Task
from app.modules.workspaces.models import PlannerEvent, Workspace, WorkspaceMembership
from app.modules.workspaces.services import WorkspaceService


@pytest_asyncio.fixture(autouse=True)
async def _create_planner_tables(db_engine):
    async with db_engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with async_sessionmaker(db_engine, expire_on_commit=False)() as db:
        await WorkspaceService.seed_defaults(db)
    yield
    async with db_engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_planner_combines_events_and_recurring_sessions(
    superuser_client,
):
    resource_response = await superuser_client.post(
        "/api/planner/resources",
        json={
            "name": "Lesson Room",
            "resource_type": "room",
        },
    )
    assert resource_response.status_code == 200
    resource_id = resource_response.json()["data"]["id"]

    event_response = await superuser_client.post(
        "/api/planner/events",
        json={
            "title": "Recording block",
            "event_type": "recording",
            "starts_at": "2026-10-20T10:00:00",
            "ends_at": "2026-10-20T11:00:00",
            "timezone": "UTC",
            "resource_id": resource_id,
        },
    )
    assert event_response.status_code == 200

    series_response = await superuser_client.post(
        "/api/planner/series",
        json={
            "title": "Weekly lesson",
            "event_type": "lesson",
            "starts_at": "2026-10-20T12:00:00",
            "ends_at": "2026-10-20T13:00:00",
            "until_date": date(2026, 10, 27).isoformat(),
            "frequency": "weekly",
            "interval": 1,
            "weekdays": [1],
        },
    )
    assert series_response.status_code == 200
    assert series_response.json()["data"]["occurrences"] == 2

    activities_response = await superuser_client.get(
        "/api/planner/activities",
        params={
            "start": "2026-10-20T00:00:00Z",
            "end": "2026-10-28T00:00:00Z",
        },
    )
    assert activities_response.status_code == 200
    activities = activities_response.json()["data"]
    assert {activity["title"] for activity in activities} == {
        "Recording block",
        "Weekly lesson",
    }
    assert len(activities) == 3
    assert all(
        activity["workspace"]["color"] == "#22c55e" for activity in activities
    )
    recording = next(
        activity for activity in activities if activity["title"] == "Recording block"
    )
    assert recording["resources"] == [
        {
            "id": resource_id,
            "name": "Lesson Room",
            "resource_type": "room",
            "status": "confirmed",
        }
    ]


@pytest.mark.asyncio
async def test_resource_booking_rejects_overlapping_activities(superuser_client):
    resource_response = await superuser_client.post(
        "/api/planner/resources",
        json={"name": "Studio A", "resource_type": "room"},
    )
    resource_id = resource_response.json()["data"]["id"]
    event_payload = {
        "title": "Session",
        "event_type": "recording",
        "starts_at": "2026-10-20T10:00:00",
        "ends_at": "2026-10-20T11:00:00",
        "timezone": "UTC",
        "resource_id": resource_id,
    }

    first = await superuser_client.post("/api/planner/events", json=event_payload)
    assert first.status_code == 200
    conflict = await superuser_client.post("/api/planner/events", json=event_payload)
    assert conflict.status_code == 409


@pytest.mark.asyncio
async def test_bahandi_team_is_retained_on_calendar_activities(superuser_client):
    team_id = "bahandi-social-media-management"
    event_response = await superuser_client.post(
        "/api/planner/events",
        json={
            "title": "Artist launch campaign",
            "event_type": "plan",
            "workspace_id": "workspace-bahandi",
            "team_id": team_id,
            "starts_at": "2026-10-20T10:00:00",
            "ends_at": "2026-10-20T11:00:00",
            "timezone": "UTC",
        },
    )
    assert event_response.status_code == 200

    response = await superuser_client.get(
        "/api/planner/activities",
        params={
            "start": "2026-10-20T00:00:00Z",
            "end": "2026-10-21T00:00:00Z",
            "team_id": team_id,
        },
        headers={"X-Workspace-ID": "workspace-bahandi"},
    )
    assert response.status_code == 200
    assert response.json()["data"][0]["team"] == {
        "id": team_id,
        "name": "Social Media Management",
    }


@pytest.mark.asyncio
async def test_planner_includes_timezone_aware_project_deadline(superuser_client, db_session):
    workspace = await db_session.get(Workspace, "workspace-bahandi")
    workspace.timezone = "Asia/Manila"
    project = Project(
        id=f"deadline-{uuid4().hex[:8]}",
        workspace_id=workspace.id,
        name="Deadline only",
        end_date=date(2026, 10, 21),
        status="active",
    )
    db_session.add(project)
    await db_session.commit()
    response = await superuser_client.get(
        "/api/planner/activities",
        params={
            "start": "2026-10-20T16:00:00Z",
            "end": "2026-10-21T16:00:00Z",
            "project_id": project.id,
        },
        headers={"X-Workspace-ID": workspace.id},
    )
    assert response.status_code == 200
    deadlines = [
        activity
        for activity in response.json()["data"]
        if activity["source_type"] == "project_deadline"
    ]
    assert len(deadlines) == 1, response.json()
    assert deadlines[0]["starts_at"].startswith("2026-10-21T00:00:00+08:00")
    assert deadlines[0]["ends_at"].startswith("2026-10-22T00:00:00+08:00")
    assert deadlines[0]["all_day"] is True


@pytest.mark.asyncio
async def test_planner_uses_project_boundaries_and_task_due_dates(
    superuser_client, db_session
):
    workspace_id = "workspace-oc-music-school"
    start_date = date(2026, 10, 21)
    end_date = date(2026, 10, 22)
    scheduled_project = Project(
        id=f"scheduled-{uuid4().hex[:8]}",
        workspace_id=workspace_id,
        name="Scheduled project",
        start_date=start_date,
        end_date=end_date,
        is_continuous=False,
        status="active",
    )
    continuous_project = Project(
        id=f"continuous-{uuid4().hex[:8]}",
        workspace_id=workspace_id,
        name="Continuous project",
        start_date=start_date,
        end_date=end_date,
        is_continuous=True,
        status="active",
    )
    task = Task(
        id=f"due-{uuid4().hex[:8]}",
        project_id=scheduled_project.id,
        workspace_id=workspace_id,
        title="Due-only task",
        due_date=datetime(2026, 10, 21),
        status="pending",
    )
    db_session.add_all([scheduled_project, continuous_project, task])
    await db_session.commit()

    response = await superuser_client.get(
        "/api/planner/activities",
        params={
            "start": "2026-10-20T00:00:00Z",
            "end": "2026-10-23T00:00:00Z",
        },
        headers={"X-Workspace-ID": workspace_id},
    )
    assert response.status_code == 200
    activities = response.json()["data"]
    project_starts = [
        activity for activity in activities
        if activity["source_type"] == "project_start"
    ]
    deadlines = [
        activity for activity in activities
        if activity["source_type"] == "project_deadline"
    ]
    due_tasks = [
        activity for activity in activities
        if activity["source_type"] == "task"
    ]
    assert {activity["source_id"] for activity in project_starts} == {
        scheduled_project.id,
        continuous_project.id,
    }
    assert [activity["source_id"] for activity in deadlines] == [
        scheduled_project.id
    ]
    assert [activity["source_id"] for activity in due_tasks] == [task.id]
    assert due_tasks[0]["starts_at"] == due_tasks[0]["ends_at"]


@pytest.mark.asyncio
async def test_supervisor_foreign_schedule_is_summary_only(
    authenticated_client, authenticated_user, db_session
):
    authenticated_user.is_superuser = False
    db_session.add(
        WorkspaceMembership(
            id=f"membership-{uuid4().hex[:8]}",
            workspace_id="workspace-one-heart",
            user_id=authenticated_user.id,
            membership_role="supervisor",
            is_home=True,
            is_active=True,
        )
    )
    foreign_workspace = await db_session.get(Workspace, "workspace-bahandi")
    foreign_workspace.timezone = "Asia/Manila"
    foreign_project = Project(
        id=f"foreign-project-{uuid4().hex[:8]}",
        workspace_id=foreign_workspace.id,
        name="Private project name",
        end_date=date(2026, 10, 21),
        status="active",
    )
    foreign_task = Task(
        id=f"foreign-task-{uuid4().hex[:8]}",
        project_id=foreign_project.id,
        workspace_id=foreign_workspace.id,
        title="Private task name",
        status="in_progress",
        due_date=datetime(2026, 10, 21, 12),
    )
    foreign_event = PlannerEvent(
        id=f"foreign-event-{uuid4().hex[:8]}",
        workspace_id="workspace-bahandi",
        title="Private rehearsal",
        description="Private notes must not be visible.",
        event_type="recording",
        status="scheduled",
        starts_at=datetime(2026, 10, 21, 10),
        ends_at=datetime(2026, 10, 21, 11),
        timezone="UTC",
        all_day=False,
    )
    db_session.add_all([foreign_project, foreign_task, foreign_event])
    await db_session.commit()

    params = {
        "start": "2026-10-20T00:00:00Z",
        "end": "2026-10-22T00:00:00Z",
    }
    summary_response = await authenticated_client.get(
        "/api/planner/activities/summary",
        params=params,
    )
    assert summary_response.status_code == 200
    summary = summary_response.json()["data"]
    assert {activity["kind"] for activity in summary} == {
        "recording",
        "task",
        "project_deadline",
    }
    recording = next(activity for activity in summary if activity["kind"] == "recording")
    assert recording["starts_at"].startswith("2026-10-21T18:00:00+08:00")
    assert all(activity["workspace"]["id"] == "workspace-bahandi" for activity in summary)
    for activity in summary:
        assert "source_id" not in activity
        assert "title" not in activity
        assert "project" not in activity
    assert "Private rehearsal" not in str(summary)
    assert "Private project name" not in str(summary)
    assert "Private task name" not in str(summary)
    assert "Private notes" not in str(summary)

    spoofed_summary_response = await authenticated_client.get(
        "/api/planner/activities/summary",
        params=params,
        headers={"X-Workspace-ID": "workspace-bahandi"},
    )
    assert spoofed_summary_response.status_code == 403

    scoped_response = await authenticated_client.get(
        "/api/planner/activities",
        params=params,
    )
    assert scoped_response.status_code == 200
    assert scoped_response.json()["data"] == []
    spoofed_workspace_response = await authenticated_client.get(
        "/api/planner/activities",
        params=params,
        headers={"X-Workspace-ID": "workspace-bahandi"},
    )
    assert spoofed_workspace_response.status_code == 403

    detail_response = await authenticated_client.get(
        f"/api/entity/planner_event/detail/{foreign_event.id}",
        headers={"X-Workspace-ID": "workspace-bahandi"},
    )
    assert detail_response.status_code in {403, 404}
    task_detail_response = await authenticated_client.get(
        f"/api/entity/task/detail/{foreign_task.id}",
        headers={"X-Workspace-ID": "workspace-bahandi"},
    )
    assert task_detail_response.status_code in {403, 404}
    project_detail_response = await authenticated_client.get(
        f"/api/entity/project/detail/{foreign_project.id}",
        headers={"X-Workspace-ID": "workspace-bahandi"},
    )
    assert project_detail_response.status_code in {403, 404}
    mutation_response = await authenticated_client.patch(
        f"/api/planner/events/{foreign_event.id}",
        json={"title": "Changed"},
        headers={"X-Workspace-ID": "workspace-bahandi"},
    )
    assert mutation_response.status_code == 403


@pytest.mark.asyncio
async def test_regular_workspace_member_cannot_request_global_schedule_summary(
    authenticated_client, authenticated_user, db_session
):
    authenticated_user.is_superuser = False
    db_session.add(
        WorkspaceMembership(
            id=f"membership-{uuid4().hex[:8]}",
            workspace_id="workspace-one-heart",
            user_id=authenticated_user.id,
            membership_role="member",
            is_home=True,
            is_active=True,
        )
    )
    await db_session.commit()

    response = await authenticated_client.get(
        "/api/planner/activities/summary",
        params={
            "start": "2026-10-20T00:00:00Z",
            "end": "2026-10-22T00:00:00Z",
        },
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_planner_range_limit_and_pagination_are_preserved(superuser_client):
    for day, title in ((20, "First page"), (21, "Second page")):
        response = await superuser_client.post(
            "/api/planner/events",
            json={
                "title": title,
                "event_type": "event",
                "starts_at": f"2026-10-{day}T10:00:00Z",
                "ends_at": f"2026-10-{day}T11:00:00Z",
                "timezone": "UTC",
            },
        )
        assert response.status_code == 200

    page = await superuser_client.get(
        "/api/planner/activities",
        params={
            "start": "2026-10-20T00:00:00Z",
            "end": "2026-10-22T00:00:00Z",
            "page": 2,
            "page_size": 1,
        },
    )
    assert page.status_code == 200
    assert page.json()["total"] == 2
    assert len(page.json()["data"]) == 1
    assert page.json()["data"][0]["title"] == "Second page"

    max_range = await superuser_client.get(
        "/api/planner/activities",
        params={
            "start": "2026-01-01T00:00:00Z",
            "end": "2027-01-02T00:00:00Z",
        },
    )
    assert max_range.status_code == 200
    too_long = await superuser_client.get(
        "/api/planner/activities",
        params={
            "start": "2026-01-01T00:00:00Z",
            "end": "2027-01-03T00:00:00Z",
        },
    )
    assert too_long.status_code == 400
