import json
from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.core.config import settings
from app.core.exceptions import BadRequestError
from app.modules.project_tasks.bahandi_integration import (
    build_artist_feed,
    press_submission_payload,
)
from app.modules.project_tasks.models import Project, Task
from app.modules.workspaces.models import PlannerEvent
from app.modules.workspaces.services import WorkspaceService


@pytest.mark.asyncio
async def test_artist_feed_requires_a_scoped_bearer_token(client):
    response = await client.get(
        "/api/integrations/bahandi/v1/artists/42/feed",
        headers={"Authorization": "Bearer invalid"},
    )

    assert response.status_code == 401


def test_press_submission_payload_uses_only_the_approved_structured_content():
    task = SimpleNamespace(id="TASK-1", integration_kind="press_release")
    project = SimpleNamespace(
        workspace_id=settings.BAHANDI_WORKSPACE_ID,
        bahandi_artist_id=42,
    )
    submission = SimpleNamespace(
        id="SUB-1",
        content=json.dumps(
            {
                "version": "oc-press-v1",
                "title": "Album announcement",
                "lead": "A short summary",
                "content": "Approved Markdown body",
                "author": "Bahandi Entertainment",
            }
        ),
    )
    approval = SimpleNamespace(id="APP-1")

    assert press_submission_payload(task, project, submission, approval) == {
        "version": "oc-press-v1",
        "sourceTaskId": "TASK-1",
        "sourceSubmissionId": "SUB-1",
        "sourceApprovalId": "APP-1",
        "artistId": 42,
        "draft": {
            "title": "Album announcement",
            "lead": "A short summary",
            "content": "Approved Markdown body",
            "author": "Bahandi Entertainment",
        },
    }


@pytest.mark.parametrize(
    "content",
    [
        "not-json",
        json.dumps({"version": "wrong"}),
        json.dumps(
            {
                "version": "oc-press-v1",
                "title": "Headline",
                "lead": "",
                "content": "body",
                "author": "Bahandi",
                "featured": True,
            }
        ),
    ],
)
def test_press_submission_payload_rejects_invalid_content(content):
    task = SimpleNamespace(id="TASK-1", integration_kind="press_release")
    project = SimpleNamespace(
        workspace_id=settings.BAHANDI_WORKSPACE_ID,
        bahandi_artist_id=42,
    )

    with pytest.raises(BadRequestError):
        press_submission_payload(
            task,
            project,
            SimpleNamespace(id="SUB-1", content=content),
            SimpleNamespace(id="APP-1"),
        )


def test_press_submission_payload_requires_bahandi_artist_mapping():
    with pytest.raises(BadRequestError, match="artist ID"):
        press_submission_payload(
            SimpleNamespace(id="TASK-1", integration_kind="press_release"),
            SimpleNamespace(
                workspace_id=settings.BAHANDI_WORKSPACE_ID,
                bahandi_artist_id=None,
            ),
            SimpleNamespace(id="SUB-1", content="{}"),
            SimpleNamespace(id="APP-1"),
        )


@pytest.mark.asyncio
async def test_artist_feed_only_contains_opted_in_public_work(db_session, monkeypatch):
    monkeypatch.setattr(settings, "BAHANDI_WORKSPACE_ID", "workspace-bahandi")
    await WorkspaceService.seed_defaults(db_session)
    project = Project(
        id=f"PROJ-{uuid4().hex[:8]}",
        name="Album Project",
        workspace_id="workspace-bahandi",
        status="active",
        bahandi_artist_id=42,
        integration_kind="album",
        artist_portal_visible=True,
        public_summary="Public project summary",
    )
    hidden_project = Project(
        id=f"PROJ-{uuid4().hex[:8]}",
        name="Internal project",
        workspace_id="workspace-bahandi",
        status="active",
        bahandi_artist_id=42,
        integration_kind="album",
        artist_portal_visible=False,
    )
    db_session.add_all([project, hidden_project])
    await db_session.flush()
    db_session.add_all(
        [
            Task(
                id=f"TASK-{uuid4().hex[:8]}",
                project_id=project.id,
                workspace_id=project.workspace_id,
                title="Public song",
                status="done",
                artist_portal_kind="song",
                public_summary="Artist-safe note",
            ),
            Task(
                id=f"TASK-{uuid4().hex[:8]}",
                project_id=project.id,
                workspace_id=project.workspace_id,
                title="Private task",
                status="in_progress",
                description="Internal-only description",
            ),
            Task(
                id=f"TASK-{uuid4().hex[:8]}",
                project_id=hidden_project.id,
                workspace_id=hidden_project.workspace_id,
                title="Hidden song",
                artist_portal_kind="song",
            ),
            PlannerEvent(
                id=str(uuid4()),
                workspace_id=project.workspace_id,
                project_id=project.id,
                title="Recording session",
                event_type="recording",
                status="scheduled",
                starts_at=datetime(2026, 11, 15, 2),
                ends_at=datetime(2026, 11, 15, 4),
                timezone="Asia/Manila",
                artist_portal_visible=True,
            ),
        ]
    )
    await db_session.flush()

    feed = await build_artist_feed(db_session, 42)

    assert [item["title"] for item in feed["projects"]] == ["Album Project"]
    assert feed["projects"][0]["description"] == "Public project summary"
    assert [item["title"] for item in feed["projects"][0]["items"]] == ["Public song"]
    assert feed["projects"][0]["items"][0]["progress"] == 100
    assert feed["projects"][0]["items"][0]["notes"] == "Artist-safe note"
    assert feed["schedules"][0]["startsAt"] == "2026-11-15T10:00:00+08:00"
