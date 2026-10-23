import asyncio
import hashlib
import hmac
import json
import secrets
from datetime import date, datetime, time, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import BadRequestError
from app.core.security import CurrentUser, is_system_admin_user
from app.modules.project_tasks.models import (
    BahandiFeedCredential,
    BahandiPressOutbox,
    Project,
    Task,
    TaskApproval,
    TaskSubmission,
)
from app.modules.workspaces.models import (
    PlannerEvent,
    ScheduleOccurrence,
    ScheduleSeries,
)

FEED_VERSION = "generic-json-v1"
PRESS_VERSION = "oc-press-v1"
FEED_LIMIT_PROJECTS = 100
FEED_LIMIT_ITEMS = 250
FEED_LIMIT_TOTAL_ITEMS = 2500
FEED_LIMIT_SCHEDULES = 500
FEED_MAX_RESPONSE_BYTES = 1_900_000
FEED_TIMEZONE = ZoneInfo("Asia/Manila")


def _contract_text_length(value: str) -> int:
    return len(value.encode("utf-16-le")) // 2


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def issue_feed_credential(db: AsyncSession, artist_id: int, actor: CurrentUser) -> str:
    if not is_system_admin_user(actor):
        raise HTTPException(status_code=403, detail="System administrator access required")
    if artist_id < 1:
        raise BadRequestError("Artist ID must be a positive integer")
    existing = await db.scalar(
        select(BahandiFeedCredential).where(BahandiFeedCredential.artist_id == artist_id)
    )
    token = secrets.token_urlsafe(32)
    if existing:
        existing.token_hash = _token_hash(token)
        existing.enabled = True
    else:
        db.add(
            BahandiFeedCredential(
                artist_id=artist_id,
                token_hash=_token_hash(token),
                enabled=True,
            )
        )
    await db.commit()
    return token


async def revoke_feed_credential(db: AsyncSession, artist_id: int, actor: CurrentUser) -> None:
    if not is_system_admin_user(actor):
        raise HTTPException(status_code=403, detail="System administrator access required")
    credential = await db.scalar(
        select(BahandiFeedCredential).where(BahandiFeedCredential.artist_id == artist_id)
    )
    if credential:
        credential.enabled = False
        await db.commit()


async def authenticate_feed(db: AsyncSession, artist_id: int, token: str | None) -> bool:
    if not token or len(token) > 256:
        return False
    credential = await db.scalar(
        select(BahandiFeedCredential).where(
            BahandiFeedCredential.artist_id == artist_id,
            BahandiFeedCredential.enabled.is_(True),
        )
    )
    if not credential:
        return False
    return hmac.compare_digest(credential.token_hash, _token_hash(token))


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _local_date(value: date | None, *, end: bool = False) -> str | None:
    if value is None:
        return None
    local_time = time.max if end else time.min
    return datetime.combine(value, local_time, FEED_TIMEZONE).isoformat()


async def build_artist_feed(db: AsyncSession, artist_id: int) -> dict:
    workspace_id = settings.BAHANDI_WORKSPACE_ID
    projects = list(
        (
            await db.scalars(
                select(Project)
                .where(
                    Project.workspace_id == workspace_id,
                    Project.bahandi_artist_id == artist_id,
                    Project.artist_portal_visible.is_(True),
                    Project.integration_kind.is_not(None),
                    Project.status.notin_(("archived", "closed")),
                )
                .order_by(Project.name, Project.id)
                .limit(FEED_LIMIT_PROJECTS + 1)
            )
        ).all()
    )
    if len(projects) > FEED_LIMIT_PROJECTS:
        raise HTTPException(status_code=413, detail="Artist feed exceeds the project limit")

    project_ids = [project.id for project in projects]
    now = datetime.now(timezone.utc)
    range_start = now - timedelta(days=30)
    range_end = now + timedelta(days=365)
    task_counts = {}
    tasks_by_project: dict[str, list[Task]] = {}
    if projects:
        counts = await db.execute(
            select(Task.project_id, func.count(Task.id))
            .where(
                Task.project_id.in_(project_ids),
                Task.artist_portal_kind.in_(("song", "milestone")),
            )
            .group_by(Task.project_id)
        )
        task_counts = dict(counts.all())
        if any(count > FEED_LIMIT_ITEMS for count in task_counts.values()):
            raise HTTPException(status_code=413, detail="Project exceeds the item limit")
        if sum(task_counts.values()) > FEED_LIMIT_TOTAL_ITEMS:
            raise HTTPException(status_code=413, detail="Artist feed exceeds the total item limit")
        tasks = list(
            (
                await db.scalars(
                    select(Task)
                    .where(
                        Task.project_id.in_(project_ids),
                        Task.artist_portal_kind.in_(("song", "milestone")),
                    )
                    .order_by(Task.project_id, Task.title, Task.id)
                )
            ).all()
        )
        for task in tasks:
            tasks_by_project.setdefault(task.project_id, []).append(task)

    feed_projects = []
    for project in projects:
        tasks = tasks_by_project.get(project.id, [])
        if (
            _contract_text_length(project.name or "") > 240
            or _contract_text_length(project.public_summary or "") > 2000
            or _contract_text_length(project.status or "active") > 80
        ):
            raise HTTPException(status_code=422, detail="Project exceeds the feed field limits")
        items = [
            {
                "id": f"oc:task:{task.id}",
                "title": task.title or "Untitled",
                "status": task.status or "open",
                "progress": 100 if task.status in {"approved", "done", "closed"} else 0,
                "dueAt": _as_utc(task.due_date).isoformat() if task.due_date else None,
                "notes": task.public_summary or "",
                "sortOrder": index,
            }
            for index, task in enumerate(tasks)
        ]
        if any(
            _contract_text_length(item["title"]) > 240
            or _contract_text_length(item["notes"]) > 2000
            or _contract_text_length(item["status"]) > 80
            for item in items
        ):
            raise HTTPException(status_code=422, detail="Project item exceeds the feed field limits")
        progress = round(sum(item["progress"] for item in items) / len(items)) if items else None
        feed_projects.append(
            {
                "id": f"oc:project:{project.id}",
                "title": project.name or "Untitled",
                "description": project.public_summary or "",
                "status": project.status or "active",
                "progress": progress,
                "startsAt": _local_date(project.start_date),
                "dueAt": _local_date(project.end_date, end=True),
                "items": items,
            }
        )

    schedules: list[dict] = []
    if project_ids:
        events = list(
            (
                await db.scalars(
                    select(PlannerEvent)
                    .where(
                        PlannerEvent.project_id.in_(project_ids),
                        PlannerEvent.artist_portal_visible.is_(True),
                        PlannerEvent.starts_at >= range_start.replace(tzinfo=None),
                        PlannerEvent.starts_at <= range_end.replace(tzinfo=None),
                    )
                    .order_by(PlannerEvent.starts_at, PlannerEvent.id)
                    .limit(FEED_LIMIT_SCHEDULES + 1)
                )
            ).all()
        )
        for event in events:
            zone = ZoneInfo(event.timezone or "UTC")
            schedules.append(
                {
                    "id": f"oc:event:{event.id}",
                    "title": event.title,
                    "type": event.event_type,
                    "startsAt": _as_utc(event.starts_at).astimezone(zone).isoformat(),
                    "endsAt": _as_utc(event.ends_at).astimezone(zone).isoformat(),
                    "allDay": event.all_day,
                    "timeZone": zone.key,
                    "location": "",
                    "status": event.status,
                }
            )
        if any(
            _contract_text_length(event.title) > 240
            or _contract_text_length(event.event_type) > 60
            or _contract_text_length(event.status) > 60
            or len(event.timezone or "UTC") > 80
            for event in events
        ):
            raise HTTPException(status_code=422, detail="Schedule exceeds the feed field limits")
        if len(events) > FEED_LIMIT_SCHEDULES:
            raise HTTPException(status_code=413, detail="Artist feed exceeds the schedule limit")

        occurrences = list(
            (
                await db.execute(
                    select(ScheduleOccurrence, ScheduleSeries)
                    .join(ScheduleSeries, ScheduleOccurrence.series_id == ScheduleSeries.id)
                    .where(
                        ScheduleSeries.project_id.in_(project_ids),
                        ScheduleSeries.artist_portal_visible.is_(True),
                        ScheduleOccurrence.starts_at >= range_start.replace(tzinfo=None),
                        ScheduleOccurrence.starts_at <= range_end.replace(tzinfo=None),
                    )
                    .order_by(ScheduleOccurrence.starts_at, ScheduleOccurrence.id)
                    .limit(FEED_LIMIT_SCHEDULES + 1)
                )
            ).all()
        )
        if len(schedules) + len(occurrences) > FEED_LIMIT_SCHEDULES:
            raise HTTPException(status_code=413, detail="Artist feed exceeds the schedule limit")
        for occurrence, series in occurrences:
            zone = ZoneInfo(series.timezone or "UTC")
            schedules.append(
                {
                    "id": f"oc:occurrence:{occurrence.id}",
                    "title": occurrence.title_override or series.title,
                    "type": series.event_type,
                    "startsAt": _as_utc(occurrence.starts_at).astimezone(zone).isoformat(),
                    "endsAt": _as_utc(occurrence.ends_at).astimezone(zone).isoformat(),
                    "allDay": False,
                    "timeZone": zone.key,
                    "location": "",
                    "status": occurrence.status,
                }
            )
        if any(
            _contract_text_length(item["title"]) > 240
            or _contract_text_length(item["type"]) > 60
            or _contract_text_length(item["status"]) > 60
            or len(item["timeZone"]) > 80
            for item in schedules
        ):
            raise HTTPException(status_code=422, detail="Schedule exceeds the feed field limits")

    schedules.sort(key=lambda item: (item["startsAt"], item["id"]))
    feed = {
        "version": FEED_VERSION,
        "generatedAt": now.isoformat(),
        "projects": feed_projects,
        "schedules": schedules,
    }
    if len(json.dumps(feed, ensure_ascii=False).encode("utf-8")) > FEED_MAX_RESPONSE_BYTES:
        raise HTTPException(status_code=413, detail="Artist feed exceeds the response size limit")
    return feed


def press_submission_payload(
    task: Task,
    project: Project,
    submission: TaskSubmission,
    approval: TaskApproval,
) -> dict | None:
    if task.integration_kind != "press_release":
        return None
    if project.workspace_id != settings.BAHANDI_WORKSPACE_ID:
        raise BadRequestError("Press-release tasks must belong to the Bahandi workspace")
    if not project.bahandi_artist_id:
        raise BadRequestError("Set the Bahandi artist ID on the press-release project")
    try:
        draft = json.loads(submission.content or "")
    except (TypeError, json.JSONDecodeError) as exc:
        raise BadRequestError("Press submission must contain valid oc-press-v1 JSON") from exc
    if not isinstance(draft, dict) or draft.get("version") != PRESS_VERSION:
        raise BadRequestError("Press submission version must be oc-press-v1")
    if set(draft) != {"version", "title", "lead", "content", "author"}:
        raise BadRequestError("Press submission contains unsupported fields")
    title = draft.get("title")
    lead = draft.get("lead")
    content = draft.get("content")
    author = draft.get("author")
    if not all(isinstance(value, str) for value in (title, lead, content, author)):
        raise BadRequestError("Press title, lead, content, and author must be text")
    if not title.strip() or _contract_text_length(title.strip()) > 250:
        raise BadRequestError("Press title must be between 1 and 250 characters")
    if (
        _contract_text_length(lead) > 2000
        or not content.strip()
        or _contract_text_length(content) > 200000
    ):
        raise BadRequestError("Press lead or body is invalid")
    if not author.strip() or _contract_text_length(author.strip()) > 160:
        raise BadRequestError("Press author must be between 1 and 160 characters")
    return {
        "version": PRESS_VERSION,
        "sourceTaskId": task.id,
        "sourceSubmissionId": submission.id,
        "sourceApprovalId": approval.id,
        "artistId": project.bahandi_artist_id,
        "draft": {
            "title": title.strip(),
            "lead": lead.strip(),
            "content": content,
            "author": author.strip(),
        },
    }


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class PermanentDeliveryError(RuntimeError):
    pass


def _send_press_payload(payload: dict) -> tuple[int, dict]:
    endpoint = settings.BAHANDI_PRESS_DRAFT_URL
    token = settings.BAHANDI_PRESS_DRAFT_TOKEN
    if not endpoint or not token:
        raise RuntimeError("Bahandi press integration is not configured")
    parsed = urlparse(endpoint)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise RuntimeError("Bahandi press endpoint must be a valid HTTPS URL")
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = Request(
        endpoint,
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    opener = build_opener(_NoRedirect)
    try:
        with opener.open(request, timeout=max(1, min(settings.BAHANDI_HTTP_TIMEOUT_SECONDS, 30))) as response:
            response_body = response.read(65537)
            if len(response_body) > 65536:
                raise RuntimeError("Bahandi press response exceeded the size limit")
            return response.status, json.loads(response_body or b"{}")
    except HTTPError as error:
        if 400 <= error.code < 500 and error.code not in {408, 429}:
            raise PermanentDeliveryError(
                f"Bahandi press endpoint returned HTTP {error.code}"
            ) from None
        raise RuntimeError(f"Bahandi press endpoint returned HTTP {error.code}") from None
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError("Could not deliver the Bahandi press draft") from exc


async def process_press_outbox(db: AsyncSession, batch_size: int = 5) -> dict[str, int]:
    now = datetime.utcnow()
    retryable = and_(
        BahandiPressOutbox.status.in_(("queued", "retrying")),
        BahandiPressOutbox.run_at <= now,
    )
    stale_processing = and_(
        BahandiPressOutbox.status == "processing",
        BahandiPressOutbox.locked_at.is_not(None),
        BahandiPressOutbox.locked_at < now - timedelta(minutes=5),
    )
    candidate_ids = list(
        (
            await db.scalars(
                select(BahandiPressOutbox.id)
                .where(
                    or_(retryable, stale_processing),
                    BahandiPressOutbox.completed_at.is_(None),
                )
                .order_by(BahandiPressOutbox.run_at, BahandiPressOutbox.id)
                .limit(max(1, min(batch_size, 3)))
            )
        ).all()
    )
    claimed_ids = []
    for outbox_id in candidate_ids:
        claimed_id = await db.scalar(
            update(BahandiPressOutbox)
            .where(
                BahandiPressOutbox.id == outbox_id,
                BahandiPressOutbox.completed_at.is_(None),
                or_(retryable, stale_processing),
            )
            .values(
                status="processing",
                locked_at=now,
                attempts=BahandiPressOutbox.attempts + 1,
            )
            .returning(BahandiPressOutbox.id)
        )
        if claimed_id is not None:
            claimed_ids.append(claimed_id)
    rows = (
        list(
            (
                await db.scalars(
                    select(BahandiPressOutbox).where(
                        BahandiPressOutbox.id.in_(claimed_ids)
                    )
                )
            ).all()
        )
        if claimed_ids
        else []
    )
    await db.commit()

    succeeded = failed = retrying = 0
    for row in rows:
        try:
            status_code, _ = await asyncio.to_thread(_send_press_payload, row.payload)
            if status_code not in (200, 201):
                raise RuntimeError(f"Bahandi press endpoint returned HTTP {status_code}")
            row.status = "completed"
            row.completed_at = datetime.utcnow()
            row.last_error = ""
            succeeded += 1
        except PermanentDeliveryError as exc:
            row.status = "failed"
            row.completed_at = datetime.utcnow()
            row.locked_at = None
            row.last_error = str(exc)[:1000]
            failed += 1
        except Exception as exc:
            row.locked_at = None
            row.last_error = str(exc)[:1000]
            if row.attempts >= 5:
                row.status = "failed"
                failed += 1
            else:
                row.status = "retrying"
                row.run_at = datetime.utcnow() + timedelta(minutes=row.attempts)
                retrying += 1
    await db.commit()
    return {"processed": len(rows), "succeeded": succeeded, "retrying": retrying, "failed": failed}
