from datetime import date

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.database import Base
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
