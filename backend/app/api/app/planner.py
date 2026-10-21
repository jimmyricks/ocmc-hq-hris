from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Literal
from uuid import uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, Header, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import and_, exists, false, func, literal, or_, select, union_all
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, get_row_scope_service
from app.application.services.access_control.row_scope_service import RowScopeService
from app.core.exceptions import BadRequestError, ConflictError, ForbiddenError, NotFoundError
from app.core.security import CurrentUser, require_authenticated_user
from app.core.serialization import record_to_dict
from app.modules.collaboration_audit.services import AuditLogService
from app.modules.project_tasks.models import Project, Task
from app.modules.workspaces.models import (
    PlannerEvent,
    ResourceBooking,
    ScheduleOccurrence,
    ScheduleSeries,
    Workspace,
    WorkspaceMembership,
    WorkspaceResource,
    WorkspaceTeam,
)
from app.modules.workspaces.services import WorkspaceService

router = APIRouter(prefix="/planner", tags=["planner"])

MAX_RANGE_DAYS = 366
MAX_SERIES_DAYS = 730
MAX_OCCURRENCES = 500


class PlannerEventCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    event_type: Literal["plan", "milestone", "event", "lesson", "recording"] = "event"
    project_id: str | None = None
    workspace_id: str | None = None
    team_id: str | None = None
    starts_at: datetime
    ends_at: datetime
    timezone: str | None = None
    all_day: bool = False
    resource_id: str | None = None


class PlannerEventUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    event_type: Literal["plan", "milestone", "event", "lesson", "recording"] | None = None
    project_id: str | None = None
    team_id: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    timezone: str | None = None
    all_day: bool | None = None
    status: Literal["scheduled", "cancelled", "completed"] | None = None


class ScheduleSeriesCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    event_type: Literal["lesson", "recording", "event"] = "lesson"
    project_id: str | None = None
    workspace_id: str | None = None
    team_id: str | None = None
    starts_at: datetime
    ends_at: datetime
    until_date: date
    frequency: Literal["daily", "weekly", "monthly"]
    interval: int = Field(default=1, ge=1, le=52)
    weekdays: list[int] = Field(default_factory=list)
    timezone: str | None = None
    resource_id: str | None = None


class WorkspaceResourceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=255)
    resource_type: Literal["room", "equipment", "instructor", "other"]
    description: str | None = None
    workspace_id: str | None = None


class WorkspaceResourceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=255)
    is_active: bool | None = None


class ResourceBookingCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resource_id: str
    event_id: str | None = None
    occurrence_id: str | None = None


class OccurrenceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["scheduled", "cancelled"] | None = None
    title_override: str | None = Field(default=None, max_length=255)


def _to_local(value: datetime, zone: ZoneInfo) -> datetime:
    if value.tzinfo is not None:
        return value.astimezone(zone)
    local = value.replace(tzinfo=zone)
    if local.astimezone(timezone.utc).astimezone(zone).replace(tzinfo=None) != value:
        raise BadRequestError("The local datetime is invalid because of a timezone transition")
    return local


def _to_utc_naive(value: datetime, zone: ZoneInfo) -> datetime:
    return _to_local(value, zone).astimezone(timezone.utc).replace(tzinfo=None)


def _zone(value: str) -> ZoneInfo:
    try:
        return ZoneInfo(value)
    except ZoneInfoNotFoundError as exc:
        raise BadRequestError("Unknown timezone") from exc


def _activity_dict(row, resources: list[dict] | None = None) -> dict:
    return {
        "id": f"{row.source_type}:{row.source_id}",
        "source_type": row.source_type,
        "source_id": row.source_id,
        "kind": row.kind,
        "title": row.title,
        "starts_at": row.starts_at.isoformat() if row.starts_at else None,
        "ends_at": row.ends_at.isoformat() if row.ends_at else None,
        "all_day": row.all_day,
        "status": row.status,
        "workspace": {
            "id": row.workspace_id,
            "name": row.workspace_name,
            "color": row.workspace_color,
        },
        "team": (
            {"id": row.team_id, "name": row.team_name}
            if row.team_id
            else None
        ),
        "project": (
            {"id": row.project_id, "name": row.project_name}
            if row.project_id
            else None
        ),
        "resources": resources or [],
    }


def _utc_naive(value: datetime) -> datetime:
    return value.astimezone(timezone.utc).replace(tzinfo=None) if value.tzinfo else value


def _validate_planner_range(start: datetime, end: datetime) -> tuple[datetime, datetime]:
    if end <= start:
        raise BadRequestError("end must be later than start")
    if end - start > timedelta(days=MAX_RANGE_DAYS):
        raise BadRequestError(f"Planner date range cannot exceed {MAX_RANGE_DAYS} days")
    return _utc_naive(start), _utc_naive(end)


async def _create_resource_booking(
    db: AsyncSession,
    user: CurrentUser,
    workspace_id: str,
    resource_id: str,
    title: str,
    starts_at: datetime,
    ends_at: datetime,
    event_id: str | None = None,
    occurrence_id: str | None = None,
) -> ResourceBooking:
    resource = await db.scalar(
        select(WorkspaceResource)
        .where(
            WorkspaceResource.id == resource_id,
            WorkspaceResource.workspace_id == workspace_id,
            WorkspaceResource.is_active.is_(True),
        )
        .with_for_update()
    )
    if not resource:
        raise NotFoundError("Workspace resource", resource_id)
    await _ensure_resource_available(
        db, resource_id, starts_at, ends_at
    )
    booking = ResourceBooking(
        id=str(uuid4()),
        workspace_id=workspace_id,
        resource_id=resource_id,
        event_id=event_id,
        occurrence_id=occurrence_id,
        title=title,
        starts_at=starts_at,
        ends_at=ends_at,
        status="confirmed",
        created_by=user.id,
        last_modified_by=user.id,
    )
    db.add(booking)
    return booking


async def _ensure_resource_available(
    db: AsyncSession,
    resource_id: str,
    starts_at: datetime,
    ends_at: datetime,
    exclude_booking_id: str | None = None,
) -> None:
    query = select(ResourceBooking.id).where(
        ResourceBooking.resource_id == resource_id,
        ResourceBooking.status != "cancelled",
        ResourceBooking.starts_at < ends_at,
        ResourceBooking.ends_at > starts_at,
    )
    if exclude_booking_id:
        query = query.where(ResourceBooking.id != exclude_booking_id)
    conflict = await db.scalar(query)
    if conflict:
        raise ConflictError("The selected resource is already booked for this time")


def _event_timezone(record: PlannerEvent, value: str | None) -> ZoneInfo:
    return _zone(value or record.timezone)


async def _event_booking(db: AsyncSession, event_id: str) -> ResourceBooking | None:
    return await db.scalar(
        select(ResourceBooking).where(
            ResourceBooking.event_id == event_id,
            ResourceBooking.status != "cancelled",
        )
    )


async def _assert_event_project(
    db: AsyncSession, workspace_id: str, project_id: str | None
) -> Project | None:
    if not project_id:
        return None
    project = await db.get(Project, project_id)
    if not project:
        raise NotFoundError("Project", project_id)
    if project.workspace_id != workspace_id:
        raise BadRequestError("Planner event and project must belong to the same workspace")
    return project


async def _assert_workspace_team(
    db: AsyncSession, workspace_id: str, team_id: str | None
) -> None:
    if not team_id:
        return
    team = await db.get(WorkspaceTeam, team_id)
    if not team or team.workspace_id != workspace_id:
        raise BadRequestError("Team must belong to the selected workspace")


@router.patch("/events/{event_id}")
async def update_planner_event(
    event_id: str,
    payload: PlannerEventUpdate,
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
    row_scope: RowScopeService = Depends(get_row_scope_service),
    workspace_id: str | None = Header(None, alias="X-Workspace-ID"),
):
    record = await db.get(PlannerEvent, event_id)
    if not record:
        raise NotFoundError("Planner event", event_id)
    if not await row_scope.can_access_record(
        record,
        "planner_event",
        current_user.id,
        current_user.role_ids,
        current_user.roles,
        current_user.is_superuser,
    ):
        raise ForbiddenError("You cannot modify this planner event")
    await WorkspaceService.require_workspace_role(
        db, current_user, record.workspace_id, "supervisor", workspace_id
    )

    updates = payload.model_dump(exclude_unset=True)
    zone = _event_timezone(record, updates.get("timezone"))
    starts_at = _to_utc_naive(
        updates.get("starts_at", record.starts_at), zone
    )
    ends_at = _to_utc_naive(
        updates.get("ends_at", record.ends_at), zone
    )
    if ends_at <= starts_at:
        raise BadRequestError("ends_at must be later than starts_at")
    project_id = updates.get("project_id", record.project_id)
    await _assert_event_project(db, record.workspace_id, project_id)
    await _assert_workspace_team(
        db, record.workspace_id, updates.get("team_id", record.team_id)
    )
    booking = await _event_booking(db, event_id)
    if booking:
        await _ensure_resource_available(
            db,
            booking.resource_id,
            starts_at,
            ends_at,
            exclude_booking_id=booking.id,
        )
        booking.starts_at = starts_at
        booking.ends_at = ends_at
        booking.title = updates.get("title", record.title)
        booking.last_modified_by = current_user.id

    old_values = record_to_dict(record)
    for field, value in updates.items():
        if field in {"starts_at", "ends_at"}:
            continue
        setattr(record, field, value)
    record.starts_at = starts_at
    record.ends_at = ends_at
    record.timezone = zone.key
    record.last_modified_by = current_user.id
    await AuditLogService.log_event(
        db,
        entity="planner_event",
        record_id=record.id,
        action="update",
        actor_id=current_user.id,
        old_values=old_values,
        new_values=record_to_dict(record),
    )
    await db.commit()
    return {"status": "success", "data": {"id": record.id, "status": record.status}}


@router.delete("/events/{event_id}")
async def cancel_planner_event(
    event_id: str,
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
    row_scope: RowScopeService = Depends(get_row_scope_service),
    workspace_id: str | None = Header(None, alias="X-Workspace-ID"),
):
    record = await db.get(PlannerEvent, event_id)
    if not record:
        raise NotFoundError("Planner event", event_id)
    if not await row_scope.can_access_record(
        record,
        "planner_event",
        current_user.id,
        current_user.role_ids,
        current_user.roles,
        current_user.is_superuser,
    ):
        raise ForbiddenError("You cannot cancel this planner event")
    await WorkspaceService.require_workspace_role(
        db, current_user, record.workspace_id, "supervisor", workspace_id
    )
    old_values = record_to_dict(record)
    record.status = "cancelled"
    record.last_modified_by = current_user.id
    await db.execute(
        ResourceBooking.__table__.update()
    .where(
            ResourceBooking.event_id == record.id,
            ResourceBooking.status != "cancelled",
        )
        .values(status="cancelled", last_modified_by=current_user.id)
    )
    await AuditLogService.log_event(
        db,
        entity="planner_event",
        record_id=record.id,
        action="update",
        actor_id=current_user.id,
        old_values=old_values,
        new_values=record_to_dict(record),
    )
    await db.commit()
    return {"status": "success", "message": "Planner event cancelled"}

def _series_dates(payload: ScheduleSeriesCreate) -> list[date]:
    first_day = payload.starts_at.date()
    if payload.until_date < first_day:
        raise BadRequestError("until_date must be on or after starts_at")
    if (payload.until_date - first_day).days > MAX_SERIES_DAYS:
        raise BadRequestError(f"Schedule series cannot exceed {MAX_SERIES_DAYS} days")
    if any(day < 0 or day > 6 for day in payload.weekdays):
        raise BadRequestError("weekdays must contain values from 0 (Monday) to 6 (Sunday)")

    selected_weekdays = set(payload.weekdays)
    if payload.frequency == "weekly" and not selected_weekdays:
        selected_weekdays.add(first_day.weekday())

    dates: list[date] = []
    cursor = first_day
    while cursor <= payload.until_date:
        days = (cursor - first_day).days
        months = (cursor.year - first_day.year) * 12 + cursor.month - first_day.month
        if payload.frequency == "daily":
            matches = days % payload.interval == 0
        elif payload.frequency == "weekly":
            weeks = (cursor - (first_day - timedelta(days=first_day.weekday()))).days // 7
            matches = weeks % payload.interval == 0 and cursor.weekday() in selected_weekdays
        else:
            matches = months % payload.interval == 0 and cursor.day == first_day.day
        if matches:
            dates.append(cursor)
            if len(dates) > MAX_OCCURRENCES:
                raise BadRequestError(f"Schedule series cannot exceed {MAX_OCCURRENCES} occurrences")
        cursor += timedelta(days=1)
    return dates


@router.get("/activities")
async def list_planner_activities(
    start: datetime,
    end: datetime,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    project_id: str | None = None,
    team_id: str | None = None,
    workspace_id: str | None = None,
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
    row_scope: RowScopeService = Depends(get_row_scope_service),
):
    start_utc, end_utc = _validate_planner_range(start, end)

    task_query = (
        select(
            literal("task").label("source_type"),
            Task.id.label("source_id"),
            literal("task").label("kind"),
            Task.title.label("title"),
            Task.due_date.label("starts_at"),
            Task.due_date.label("ends_at"),
            literal(False).label("all_day"),
            Task.status.label("status"),
            Project.workspace_id.label("workspace_id"),
            Workspace.name.label("workspace_name"),
            Workspace.color.label("workspace_color"),
            Project.id.label("project_id"),
            Project.name.label("project_name"),
            Project.team_id.label("team_id"),
            WorkspaceTeam.name.label("team_name"),
        )
        .join(Project, Project.id == Task.project_id)
        .join(Workspace, Workspace.id == Project.workspace_id)
        .outerjoin(WorkspaceTeam, WorkspaceTeam.id == Project.team_id)
        .where(
            Task.due_date.is_not(None),
            Task.due_date >= start_utc,
            Task.due_date < end_utc,
        )
    )
    if project_id:
        task_query = task_query.where(Task.project_id == project_id)
    if team_id:
        task_query = task_query.where(Project.team_id == team_id)
    if workspace_id:
        task_query = task_query.where(Project.workspace_id == workspace_id)
    task_query = await row_scope.apply_scope_to_query(
        task_query,
        Task,
        "task",
        current_user.id,
        current_user.role_ids,
        current_user.roles,
        current_user.is_superuser,
    )

    event_query = (
        select(
            literal("planner_event").label("source_type"),
            PlannerEvent.id.label("source_id"),
            PlannerEvent.event_type.label("kind"),
            PlannerEvent.title.label("title"),
            PlannerEvent.starts_at.label("starts_at"),
            PlannerEvent.ends_at.label("ends_at"),
            PlannerEvent.all_day.label("all_day"),
            PlannerEvent.status.label("status"),
            PlannerEvent.workspace_id.label("workspace_id"),
            Workspace.name.label("workspace_name"),
            Workspace.color.label("workspace_color"),
            Project.id.label("project_id"),
            Project.name.label("project_name"),
            PlannerEvent.team_id.label("team_id"),
            WorkspaceTeam.name.label("team_name"),
        )
        .join(Workspace, Workspace.id == PlannerEvent.workspace_id)
        .outerjoin(Project, Project.id == PlannerEvent.project_id)
        .outerjoin(WorkspaceTeam, WorkspaceTeam.id == PlannerEvent.team_id)
        .where(
            PlannerEvent.starts_at < end_utc,
            PlannerEvent.ends_at > start_utc,
        )
    )
    if project_id:
        event_query = event_query.where(PlannerEvent.project_id == project_id)
    if team_id:
        event_query = event_query.where(PlannerEvent.team_id == team_id)
    if workspace_id:
        event_query = event_query.where(PlannerEvent.workspace_id == workspace_id)
    event_query = await row_scope.apply_scope_to_query(
        event_query,
        PlannerEvent,
        "planner_event",
        current_user.id,
        current_user.role_ids,
        current_user.roles,
        current_user.is_superuser,
    )

    occurrence_query = (
        select(
            literal("schedule_occurrence").label("source_type"),
            ScheduleOccurrence.id.label("source_id"),
            ScheduleSeries.event_type.label("kind"),
            func.coalesce(
                ScheduleOccurrence.title_override, ScheduleSeries.title
            ).label("title"),
            ScheduleOccurrence.starts_at.label("starts_at"),
            ScheduleOccurrence.ends_at.label("ends_at"),
            literal(False).label("all_day"),
            ScheduleOccurrence.status.label("status"),
            ScheduleSeries.workspace_id.label("workspace_id"),
            Workspace.name.label("workspace_name"),
            Workspace.color.label("workspace_color"),
            Project.id.label("project_id"),
            Project.name.label("project_name"),
            ScheduleSeries.team_id.label("team_id"),
            WorkspaceTeam.name.label("team_name"),
        )
        .join(ScheduleSeries, ScheduleSeries.id == ScheduleOccurrence.series_id)
        .join(Workspace, Workspace.id == ScheduleSeries.workspace_id)
        .outerjoin(Project, Project.id == ScheduleSeries.project_id)
        .outerjoin(WorkspaceTeam, WorkspaceTeam.id == ScheduleSeries.team_id)
        .where(
            ScheduleOccurrence.starts_at < end_utc,
            ScheduleOccurrence.ends_at > start_utc,
            ScheduleOccurrence.status != "cancelled",
        )
    )
    if project_id:
        occurrence_query = occurrence_query.where(ScheduleSeries.project_id == project_id)
    if team_id:
        occurrence_query = occurrence_query.where(ScheduleSeries.team_id == team_id)
    if workspace_id:
        occurrence_query = occurrence_query.where(ScheduleSeries.workspace_id == workspace_id)
    occurrence_query = await row_scope.apply_scope_to_query(
        occurrence_query,
        ScheduleOccurrence,
        "schedule_occurrence",
        current_user.id,
        current_user.role_ids,
        current_user.roles,
        current_user.is_superuser,
    )

    workspace_rows = (
        await db.execute(
            select(Workspace.id, Workspace.timezone).where(Workspace.is_active.is_(True))
        )
    ).all()
    boundary_conditions = []
    workspace_zones: dict[str, ZoneInfo] = {}
    workspace_date_ranges: dict[str, tuple[date, date]] = {}
    for workspace_row in workspace_rows:
        zone = _zone(workspace_row.timezone)
        workspace_zones[workspace_row.id] = zone
        local_start = start.astimezone(zone) if start.tzinfo else start.replace(tzinfo=timezone.utc).astimezone(zone)
        local_last_instant = end - timedelta(microseconds=1)
        if local_last_instant.tzinfo is None:
            local_last_instant = local_last_instant.replace(tzinfo=timezone.utc)
        local_end = local_last_instant.astimezone(zone)
        workspace_date_ranges[workspace_row.id] = (
            local_start.date(),
            local_end.date(),
        )
        boundary_conditions.append(
            and_(
                Project.workspace_id == workspace_row.id,
                or_(
                    and_(
                        Project.start_date.is_not(None),
                        Project.start_date >= local_start.date(),
                        Project.start_date <= local_end.date(),
                    ),
                    and_(
                        Project.is_continuous.is_(False),
                        Project.end_date.is_not(None),
                        Project.end_date >= local_start.date(),
                        Project.end_date <= local_end.date(),
                    ),
                ),
            )
        )
    project_schedule_query = (
        select(
            Project.id.label("project_id"),
            Project.name.label("project_name"),
            Project.workspace_id.label("workspace_id"),
            Workspace.name.label("workspace_name"),
            Workspace.color.label("workspace_color"),
            Project.team_id.label("team_id"),
            WorkspaceTeam.name.label("team_name"),
            Project.start_date.label("start_date"),
            Project.end_date.label("end_date"),
            Project.is_continuous.label("is_continuous"),
            Project.status.label("status"),
        )
        .join(Workspace, Workspace.id == Project.workspace_id)
        .outerjoin(WorkspaceTeam, WorkspaceTeam.id == Project.team_id)
        .where(
            or_(*boundary_conditions) if boundary_conditions else false(),
        )
    )
    if project_id:
        project_schedule_query = project_schedule_query.where(Project.id == project_id)
    if team_id:
        project_schedule_query = project_schedule_query.where(Project.team_id == team_id)
    if workspace_id:
        project_schedule_query = project_schedule_query.where(
            Project.workspace_id == workspace_id
        )
    project_schedule_query = await row_scope.apply_scope_to_query(
        project_schedule_query,
        Project,
        "project",
        current_user.id,
        current_user.role_ids,
        current_user.roles,
        current_user.is_superuser,
    )
    project_schedule_rows = (await db.execute(project_schedule_query)).all()

    activities = union_all(task_query, event_query, occurrence_query).subquery()
    base_total = await db.scalar(select(func.count()).select_from(activities))
    result = await db.execute(
        select(activities)
        .order_by(
            activities.c.starts_at,
            activities.c.source_type,
            activities.c.source_id,
        )
        .limit(page * page_size)
    )
    all_rows = list(result.all())
    project_activities = []
    for project_row in project_schedule_rows:
        zone = workspace_zones[project_row.workspace_id]
        local_start_date, local_end_date = workspace_date_ranges[
            project_row.workspace_id
        ]
        milestones = (
            ("project_start", project_row.start_date, "starts"),
            (
                "project_deadline",
                project_row.end_date if not project_row.is_continuous else None,
                "deadline",
            ),
        )
        for source_type, milestone_date, label in milestones:
            if (
                milestone_date is None
                or milestone_date < local_start_date
                or milestone_date > local_end_date
            ):
                continue
            starts_at = datetime.combine(
                milestone_date, datetime.min.time(), tzinfo=zone
            )
            project_activities.append(
                SimpleNamespace(
                    source_type=source_type,
                    source_id=project_row.project_id,
                    kind=source_type,
                    title=f"{project_row.project_name} {label}",
                    starts_at=starts_at,
                    ends_at=starts_at + timedelta(days=1),
                    all_day=True,
                    status=project_row.status or "active",
                    workspace_id=project_row.workspace_id,
                    workspace_name=project_row.workspace_name,
                    workspace_color=project_row.workspace_color,
                    project_id=project_row.project_id,
                    project_name=project_row.project_name,
                    team_id=project_row.team_id,
                    team_name=project_row.team_name,
                )
            )
    all_rows.extend(project_activities)

    all_rows.sort(
        key=lambda row: (
            _utc_naive(row.starts_at),
            row.source_type,
            row.source_id,
        )
    )
    total = (base_total or 0) + len(project_activities)
    rows = all_rows[(page - 1) * page_size : page * page_size]
    resource_bookings: dict[tuple[str, str], list[dict]] = {}
    event_ids = [
        row.source_id for row in rows if row.source_type == "planner_event"
    ]
    occurrence_ids = [
        row.source_id for row in rows if row.source_type == "schedule_occurrence"
    ]
    if event_ids or occurrence_ids:
        booking_conditions = []
        if event_ids:
            booking_conditions.append(ResourceBooking.event_id.in_(event_ids))
        if occurrence_ids:
            booking_conditions.append(
                ResourceBooking.occurrence_id.in_(occurrence_ids)
            )
        booking_rows = await db.execute(
            select(ResourceBooking, WorkspaceResource)
            .join(
                WorkspaceResource,
                and_(
                    WorkspaceResource.id == ResourceBooking.resource_id,
                    WorkspaceResource.workspace_id == ResourceBooking.workspace_id,
                ),
            )
            .where(or_(*booking_conditions))
            .order_by(ResourceBooking.created_at, ResourceBooking.id)
        )
        activity_workspaces = {
            (row.source_type, row.source_id): row.workspace_id for row in rows
        }
        for booking, resource in booking_rows.all():
            if booking.event_id:
                key = ("planner_event", booking.event_id)
            elif booking.occurrence_id:
                key = ("schedule_occurrence", booking.occurrence_id)
            else:
                continue
            if booking.workspace_id != activity_workspaces.get(key):
                continue
            resource_bookings.setdefault(key, []).append(
                {
                    "id": resource.id,
                    "name": resource.name,
                    "resource_type": resource.resource_type,
                    "status": booking.status,
                }
            )
    return {
        "status": "success",
        "data": [
            _activity_dict(
                row,
                resources=resource_bookings.get(
                    (row.source_type, row.source_id), []
                ),
            )
            for row in rows
        ],
        "total": total or 0,
        "page": page,
        "page_size": page_size,
    }


@router.post("/events")
async def create_planner_event(
    payload: PlannerEventCreate,
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
    row_scope: RowScopeService = Depends(get_row_scope_service),
):
    data = await row_scope.prepare_create_data(
        "planner_event",
        payload.model_dump(include={"workspace_id", "project_id", "team_id"}),
        current_user,
    )
    project = await db.get(Project, payload.project_id) if payload.project_id else None
    if payload.project_id and not project:
        raise NotFoundError("Project", payload.project_id)
    if project and project.workspace_id != data["workspace_id"]:
        raise BadRequestError("Planner event and project must belong to the same workspace")
    await _assert_workspace_team(db, data["workspace_id"], payload.team_id)
    workspace = await db.get(Workspace, data["workspace_id"])
    zone = _zone(payload.timezone or workspace.timezone)
    starts_at = _to_utc_naive(payload.starts_at, zone)
    ends_at = _to_utc_naive(payload.ends_at, zone)
    if ends_at <= starts_at:
        raise BadRequestError("ends_at must be later than starts_at")

    record = PlannerEvent(
        id=str(uuid4()),
        **data,
        title=payload.title,
        description=payload.description,
        event_type=payload.event_type,
        starts_at=starts_at,
        ends_at=ends_at,
        timezone=zone.key,
        all_day=payload.all_day,
        created_by=current_user.id,
        last_modified_by=current_user.id,
    )
    db.add(record)
    if payload.resource_id:
        await _create_resource_booking(
            db,
            current_user,
            record.workspace_id,
            payload.resource_id,
            record.title,
            record.starts_at,
            record.ends_at,
            event_id=record.id,
        )
    await AuditLogService.log_event(
        db,
        entity="planner_event",
        record_id=record.id,
        action="create",
        actor_id=current_user.id,
        old_values=None,
        new_values=record_to_dict(record),
    )
    await db.commit()
    await db.refresh(record)
    return {"status": "success", "data": {"id": record.id, "workspace_id": record.workspace_id}}


@router.get("/activities/summary")
async def list_foreign_schedule_summary(
    start: datetime,
    end: datetime,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    workspace_id: str | None = None,
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
    active_workspace_id: str | None = Header(None, alias="X-Workspace-ID"),
):
    """Return coordination-only schedule projections outside supervisor workspaces."""
    start_utc, end_utc = _validate_planner_range(start, end)
    supervisor_workspace_ids = set(
        (
            await db.scalars(
                select(WorkspaceMembership.workspace_id).where(
                    WorkspaceMembership.user_id == current_user.id,
                    WorkspaceMembership.membership_role == "supervisor",
                    WorkspaceMembership.is_active.is_(True),
                )
            )
        ).all()
    )
    if not supervisor_workspace_ids:
        raise ForbiddenError("Global schedule summaries are only available to supervisors")
    context = await WorkspaceService.resolve_context(
        db,
        current_user.id,
        current_user.roles,
        current_user.is_superuser,
        active_workspace_id,
    )
    active_workspace_id = context.active_workspace_id
    if not active_workspace_id:
        raise ForbiddenError("Select an assigned workspace to view schedule summaries")

    summary_rows = []
    task_query = (
        select(
            literal("task").label("kind"),
            Task.due_date.label("starts_at"),
            Task.due_date.label("ends_at"),
            Task.status.label("status"),
            Project.workspace_id.label("workspace_id"),
            Workspace.name.label("workspace_name"),
            Workspace.color.label("workspace_color"),
            Workspace.timezone.label("workspace_timezone"),
            literal(False).label("all_day"),
            literal(None).label("has_resource"),
        )
        .join(Project, Project.id == Task.project_id)
        .join(Workspace, Workspace.id == Project.workspace_id)
        .where(
            Project.workspace_id != active_workspace_id,
            Workspace.is_active.is_(True),
            Task.due_date.is_not(None),
            Task.due_date >= start_utc,
            Task.due_date < end_utc,
        )
    )
    if workspace_id:
        task_query = task_query.where(Project.workspace_id == workspace_id)
    summary_rows.extend((await db.execute(task_query)).all())

    event_query = (
        select(
            PlannerEvent.event_type.label("kind"),
            PlannerEvent.starts_at.label("starts_at"),
            PlannerEvent.ends_at.label("ends_at"),
            PlannerEvent.status.label("status"),
            Workspace.id.label("workspace_id"),
            Workspace.name.label("workspace_name"),
            Workspace.color.label("workspace_color"),
            Workspace.timezone.label("workspace_timezone"),
            PlannerEvent.all_day.label("all_day"),
            exists()
            .where(
                ResourceBooking.event_id == PlannerEvent.id,
                ResourceBooking.status != "cancelled",
            )
            .label("has_resource"),
        )
        .join(Workspace, Workspace.id == PlannerEvent.workspace_id)
        .where(
            PlannerEvent.workspace_id != active_workspace_id,
            Workspace.is_active.is_(True),
            PlannerEvent.starts_at < end_utc,
            PlannerEvent.ends_at > start_utc,
        )
    )
    if workspace_id:
        event_query = event_query.where(PlannerEvent.workspace_id == workspace_id)
    summary_rows.extend((await db.execute(event_query)).all())

    occurrence_query = (
        select(
            ScheduleSeries.event_type.label("kind"),
            ScheduleOccurrence.starts_at.label("starts_at"),
            ScheduleOccurrence.ends_at.label("ends_at"),
            ScheduleOccurrence.status.label("status"),
            Workspace.id.label("workspace_id"),
            Workspace.name.label("workspace_name"),
            Workspace.color.label("workspace_color"),
            Workspace.timezone.label("workspace_timezone"),
            literal(False).label("all_day"),
            exists()
            .where(
                ResourceBooking.occurrence_id == ScheduleOccurrence.id,
                ResourceBooking.status != "cancelled",
            )
            .label("has_resource"),
        )
        .join(ScheduleSeries, ScheduleSeries.id == ScheduleOccurrence.series_id)
        .join(Workspace, Workspace.id == ScheduleSeries.workspace_id)
        .where(
            ScheduleSeries.workspace_id != active_workspace_id,
            Workspace.is_active.is_(True),
            ScheduleOccurrence.starts_at < end_utc,
            ScheduleOccurrence.ends_at > start_utc,
            ScheduleOccurrence.status != "cancelled",
        )
    )
    if workspace_id:
        occurrence_query = occurrence_query.where(
            ScheduleSeries.workspace_id == workspace_id
        )
    summary_rows.extend((await db.execute(occurrence_query)).all())

    foreign_workspaces_query = select(Workspace).where(
        Workspace.is_active.is_(True),
        Workspace.id != active_workspace_id,
    )
    if workspace_id:
        foreign_workspaces_query = foreign_workspaces_query.where(
            Workspace.id == workspace_id
        )
    foreign_workspaces = list((await db.scalars(foreign_workspaces_query)).all())
    for workspace in foreign_workspaces:
        zone = _zone(workspace.timezone)
        local_start = start_utc.replace(tzinfo=timezone.utc).astimezone(zone)
        local_end = (end_utc - timedelta(microseconds=1)).replace(
            tzinfo=timezone.utc
        ).astimezone(zone)
        projects = await db.execute(
            select(
                Project.start_date,
                Project.end_date,
                Project.is_continuous,
                Project.status,
            ).where(
                Project.workspace_id == workspace.id,
                or_(
                    and_(
                        Project.start_date.is_not(None),
                        Project.start_date >= local_start.date(),
                        Project.start_date <= local_end.date(),
                    ),
                    and_(
                        Project.is_continuous.is_(False),
                        Project.end_date.is_not(None),
                        Project.end_date >= local_start.date(),
                        Project.end_date <= local_end.date(),
                    ),
                ),
            )
        )
        for start_date, end_date, is_continuous, status in projects.all():
            milestones = (
                ("project_start", start_date),
                ("project_deadline", end_date if not is_continuous else None),
            )
            for kind, milestone_date in milestones:
                if milestone_date is None:
                    continue
                summary_rows.append(
                    {
                        "kind": kind,
                        "starts_at": datetime.combine(
                            milestone_date, datetime.min.time(), tzinfo=zone
                        ),
                        "ends_at": datetime.combine(
                            milestone_date + timedelta(days=1),
                            datetime.min.time(),
                            tzinfo=zone,
                        ),
                        "status": status or "active",
                        "workspace_id": workspace.id,
                        "workspace_name": workspace.name,
                        "workspace_color": workspace.color,
                        "all_day": True,
                        "has_resource": False,
                    }
                )

    summary_rows.sort(
        key=lambda row: (
            _utc_naive(
                row["starts_at"] if isinstance(row, dict) else row.starts_at
            ),
            row["workspace_id"] if isinstance(row, dict) else row.workspace_id,
        )
    )
    total = len(summary_rows)
    page_rows = summary_rows[(page - 1) * page_size : page * page_size]
    data = []
    for row in page_rows:
        value = row if isinstance(row, dict) else row._mapping
        starts_at = value["starts_at"]
        ends_at = value["ends_at"]
        zone = _zone(value.get("workspace_timezone") or "UTC")
        if starts_at and starts_at.tzinfo is None:
            starts_at = starts_at.replace(tzinfo=timezone.utc).astimezone(zone)
        if ends_at and ends_at.tzinfo is None:
            ends_at = ends_at.replace(tzinfo=timezone.utc).astimezone(zone)
        data.append(
            {
                "kind": value["kind"],
                "starts_at": starts_at.isoformat() if starts_at else None,
                "ends_at": ends_at.isoformat() if ends_at else None,
                "all_day": value["all_day"],
                "status": value["status"],
                "workspace": {
                    "id": value["workspace_id"],
                    "name": value["workspace_name"],
                    "color": value["workspace_color"],
                },
                "resource_label": (
                    "Resource booked" if value.get("has_resource") else None
                ),
            }
        )
    return {
        "status": "success",
        "data": data,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/series")
async def create_schedule_series(
    payload: ScheduleSeriesCreate,
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
    row_scope: RowScopeService = Depends(get_row_scope_service),
):
    data = await row_scope.prepare_create_data(
        "schedule_series",
        payload.model_dump(include={"workspace_id", "project_id", "team_id"}),
        current_user,
    )
    project = await db.get(Project, payload.project_id) if payload.project_id else None
    if payload.project_id and not project:
        raise NotFoundError("Project", payload.project_id)
    if project and project.workspace_id != data["workspace_id"]:
        raise BadRequestError("Schedule series and project must belong to the same workspace")
    await _assert_workspace_team(db, data["workspace_id"], payload.team_id)
    workspace = await db.get(Workspace, data["workspace_id"])
    zone = _zone(payload.timezone or workspace.timezone)
    local_start = _to_local(payload.starts_at, zone)
    local_end = _to_local(payload.ends_at, zone)
    if local_end <= local_start:
        raise BadRequestError("ends_at must be later than starts_at")
    dates = _series_dates(payload)
    series = ScheduleSeries(
        id=str(uuid4()),
        **data,
        title=payload.title,
        description=payload.description,
        event_type=payload.event_type,
        frequency=payload.frequency,
        interval=payload.interval,
        weekdays=",".join(str(day) for day in sorted(set(payload.weekdays))),
        starts_at=_to_utc_naive(local_start, zone),
        ends_at=_to_utc_naive(local_end, zone),
        until_date=payload.until_date,
        timezone=zone.key,
        created_by=current_user.id,
        last_modified_by=current_user.id,
    )
    db.add(series)
    await db.flush()

    day_offset = local_end.date() - local_start.date()
    for occurrence_date in dates:
        occurrence_start_local = datetime.combine(
            occurrence_date, local_start.timetz().replace(tzinfo=None), tzinfo=zone
        )
        occurrence_end_local = datetime.combine(
            occurrence_date + day_offset,
            local_end.timetz().replace(tzinfo=None),
            tzinfo=zone,
        )
        occurrence = ScheduleOccurrence(
            id=str(uuid4()),
            series_id=series.id,
            starts_at=_to_utc_naive(occurrence_start_local, zone),
            ends_at=_to_utc_naive(occurrence_end_local, zone),
            status="scheduled",
            created_by=current_user.id,
            last_modified_by=current_user.id,
        )
        db.add(occurrence)
        await db.flush()
        if payload.resource_id:
            await _create_resource_booking(
                db,
                current_user,
                series.workspace_id,
                payload.resource_id,
                series.title,
                occurrence.starts_at,
                occurrence.ends_at,
                occurrence_id=occurrence.id,
            )

    await AuditLogService.log_event(
        db,
        entity="schedule_series",
        record_id=series.id,
        action="create",
        actor_id=current_user.id,
        old_values=None,
        new_values=record_to_dict(series),
    )
    await db.commit()
    return {
        "status": "success",
        "data": {"id": series.id, "workspace_id": series.workspace_id, "occurrences": len(dates)},
    }


@router.get("/resources")
async def list_workspace_resources(
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
    row_scope: RowScopeService = Depends(get_row_scope_service),
    workspace_id: str | None = None,
):
    base_query = select(WorkspaceResource).where(WorkspaceResource.is_active.is_(True))
    if workspace_id:
        base_query = base_query.where(WorkspaceResource.workspace_id == workspace_id)
    query = await row_scope.apply_scope_to_query(
        base_query,
        WorkspaceResource,
        "workspace_resource",
        current_user.id,
        current_user.role_ids,
        current_user.roles,
        current_user.is_superuser,
    )
    result = await db.execute(query.order_by(WorkspaceResource.name))
    return {
        "status": "success",
        "data": [
            {
                "id": resource.id,
                "workspace_id": resource.workspace_id,
                "name": resource.name,
                "resource_type": resource.resource_type,
                "description": resource.description,
            }
            for resource in result.scalars().all()
        ],
    }


@router.patch("/resources/{resource_id}")
async def update_workspace_resource(
    resource_id: str,
    payload: WorkspaceResourceUpdate,
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
    workspace_id: str | None = Header(None, alias="X-Workspace-ID"),
):
    resource = await db.get(WorkspaceResource, resource_id)
    if not resource:
        raise NotFoundError("Workspace resource", resource_id)
    await WorkspaceService.require_workspace_role(
        db, current_user, resource.workspace_id, "supervisor", workspace_id
    )
    old_values = record_to_dict(resource)
    updates = payload.model_dump(exclude_unset=True)
    if "name" in updates:
        resource.name = updates["name"]
    if "is_active" in updates:
        resource.is_active = updates["is_active"]
    resource.last_modified_by = current_user.id
    await AuditLogService.log_event(
        db,
        entity="workspace_resource",
        record_id=resource.id,
        action="update",
        actor_id=current_user.id,
        old_values=old_values,
        new_values=record_to_dict(resource),
    )
    await db.commit()
    return {"status": "success", "data": {"id": resource.id, "is_active": resource.is_active}}


@router.post("/resources")
async def create_workspace_resource(
    payload: WorkspaceResourceCreate,
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
    row_scope: RowScopeService = Depends(get_row_scope_service),
):
    data = await row_scope.prepare_create_data(
        "workspace_resource", payload.model_dump(include={"workspace_id"}), current_user
    )
    record = WorkspaceResource(
        id=str(uuid4()),
        **data,
        name=payload.name,
        resource_type=payload.resource_type,
        description=payload.description,
        is_active=True,
        created_by=current_user.id,
        last_modified_by=current_user.id,
    )
    db.add(record)
    await AuditLogService.log_event(
        db,
        entity="workspace_resource",
        record_id=record.id,
        action="create",
        actor_id=current_user.id,
        old_values=None,
        new_values=record_to_dict(record),
    )
    await db.commit()
    await db.refresh(record)
    return {"status": "success", "data": {"id": record.id, "workspace_id": record.workspace_id}}


@router.post("/bookings")
async def create_resource_booking(
    payload: ResourceBookingCreate,
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
    row_scope: RowScopeService = Depends(get_row_scope_service),
    workspace_id: str | None = Header(None, alias="X-Workspace-ID"),
):
    if bool(payload.event_id) == bool(payload.occurrence_id):
        raise BadRequestError("Provide exactly one event_id or occurrence_id")
    if payload.event_id:
        record = await db.get(PlannerEvent, payload.event_id)
        if not record:
            raise NotFoundError("Planner event", payload.event_id)
        entity = "planner_event"
        starts_at, ends_at, title = record.starts_at, record.ends_at, record.title
        target_workspace = record.workspace_id
    else:
        record = await db.get(ScheduleOccurrence, payload.occurrence_id)
        if not record:
            raise NotFoundError("Schedule occurrence", payload.occurrence_id)
        series = await db.get(ScheduleSeries, record.series_id)
        if not series:
            raise NotFoundError("Schedule series", record.series_id)
        entity = "schedule_occurrence"
        starts_at, ends_at = record.starts_at, record.ends_at
        title = record.title_override or series.title
        target_workspace = series.workspace_id

    if not await row_scope.can_access_record(
        record,
        entity,
        current_user.id,
        current_user.role_ids,
        current_user.roles,
        current_user.is_superuser,
    ):
        raise ForbiddenError("You cannot book a resource for this activity")
    await WorkspaceService.require_workspace_role(
        db, current_user, target_workspace, "supervisor", workspace_id
    )
    booking = await _create_resource_booking(
        db,
        current_user,
        target_workspace,
        payload.resource_id,
        title,
        starts_at,
        ends_at,
        event_id=payload.event_id,
        occurrence_id=payload.occurrence_id,
    )
    await AuditLogService.log_event(
        db,
        entity="resource_booking",
        record_id=booking.id,
        action="create",
        actor_id=current_user.id,
        old_values=None,
        new_values=record_to_dict(booking),
    )
    await db.commit()
    return {"status": "success", "data": {"id": booking.id, "status": booking.status}}


@router.patch("/occurrences/{occurrence_id}")
async def update_schedule_occurrence(
    occurrence_id: str,
    payload: OccurrenceUpdate,
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
    row_scope: RowScopeService = Depends(get_row_scope_service),
    workspace_id: str | None = Header(None, alias="X-Workspace-ID"),
):
    occurrence = await db.get(ScheduleOccurrence, occurrence_id)
    if not occurrence:
        raise NotFoundError("Schedule occurrence", occurrence_id)
    series = await db.get(ScheduleSeries, occurrence.series_id)
    if not series:
        raise NotFoundError("Schedule series", occurrence.series_id)
    if not await row_scope.can_access_record(
        occurrence,
        "schedule_occurrence",
        current_user.id,
        current_user.role_ids,
        current_user.roles,
        current_user.is_superuser,
    ):
        raise ForbiddenError("You cannot modify this schedule occurrence")
    await WorkspaceService.require_workspace_role(
        db, current_user, series.workspace_id, "supervisor", workspace_id
    )
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(occurrence, field, value)
    occurrence.last_modified_by = current_user.id
    if occurrence.status == "cancelled":
        await db.execute(
            ResourceBooking.__table__.update()
            .where(ResourceBooking.occurrence_id == occurrence.id)
            .values(status="cancelled", last_modified_by=current_user.id)
        )
    await AuditLogService.log_event(
        db,
        entity="schedule_occurrence",
        record_id=occurrence.id,
        action="update",
        actor_id=current_user.id,
        old_values=None,
        new_values=record_to_dict(occurrence),
    )
    await db.commit()
    return {"status": "success", "data": {"id": occurrence.id, "status": occurrence.status}}


@router.delete("/bookings/{booking_id}")
async def cancel_resource_booking(
    booking_id: str,
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
    workspace_id: str | None = Header(None, alias="X-Workspace-ID"),
):
    booking = await db.get(ResourceBooking, booking_id)
    if not booking:
        raise NotFoundError("Resource booking", booking_id)
    await WorkspaceService.require_workspace_role(
        db, current_user, booking.workspace_id, "supervisor", workspace_id
    )
    booking.status = "cancelled"
    booking.last_modified_by = current_user.id
    await AuditLogService.log_event(
        db,
        entity="resource_booking",
        record_id=booking.id,
        action="update",
        actor_id=current_user.id,
        old_values=None,
        new_values=record_to_dict(booking),
    )
    await db.commit()
    return {"status": "success", "message": "Resource booking cancelled"}
