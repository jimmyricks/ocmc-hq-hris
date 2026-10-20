"""
Project & Task per-entity API hooks.

Registers the project/task entity APIs used by the generic CRUD layer.
"""
from datetime import datetime
from typing import Any

from app.application.services.base_entity_api import BaseEntityAPI, Context, register_entity_api
from app.core.serialization import record_to_dict
from app.modules.collaboration_audit.services import AuditLogService
from app.modules.project_tasks.services import ProjectTaskService


class AuditedEntityAPI(BaseEntityAPI):
    """Base API that writes an OcAuditLog row for every create/update/delete."""

    async def before_update(self, record: Any, data: dict[str, Any], ctx: Context) -> dict[str, Any]:
        ctx.extra["old_values"] = record_to_dict(record)
        return data

    async def after_create(self, record: Any, ctx: Context) -> None:
        await AuditLogService.log_event(
            ctx.db,
            entity=ctx.meta.name,
            record_id=record.id,
            action="create",
            actor_id=ctx.user.id,
            old_values=None,
            new_values=record_to_dict(record),
        )
        await ctx.db.commit()

    async def after_update(self, record: Any, ctx: Context) -> None:
        old_values = ctx.extra.get("old_values")
        await AuditLogService.log_event(
            ctx.db,
            entity=ctx.meta.name,
            record_id=record.id,
            action="update",
            actor_id=ctx.user.id,
            old_values=old_values,
            new_values=record_to_dict(record),
        )

    async def after_delete(self, ctx: Context) -> None:
        record_id = ctx.extra.get("record_id")
        old_values = ctx.extra.get("old_values")
        await AuditLogService.log_event(
            ctx.db,
            entity=ctx.meta.name,
            record_id=record_id,
            action="delete",
            actor_id=ctx.user.id,
            old_values=old_values,
            new_values=None,
        )
        await ctx.db.commit()


class ProjectAPI(AuditedEntityAPI):
    """Project business hooks."""


class ProjectMemberAPI(AuditedEntityAPI):
    """Project Member business hooks: set defaults on create."""

    async def before_create(self, data: dict[str, Any], ctx: Context) -> dict[str, Any]:
        data.setdefault("joined_at", datetime.utcnow())
        data.setdefault("is_active", True)
        data.setdefault("role", "member")
        return data


class TaskTypeAPI(AuditedEntityAPI):
    """TaskType business hooks."""


class TaskAPI(AuditedEntityAPI):
    """Task business hooks: generate task_key after create and audit."""

    async def after_create(self, record: Any, ctx: Context) -> None:
        await ProjectTaskService.finalize_task(record, ctx.db)
        await super().after_create(record, ctx)


class TaskAssignmentAPI(AuditedEntityAPI):
    """TaskAssignment business hooks: set defaults and notify/audit on create."""

    async def before_create(self, data: dict[str, Any], ctx: Context) -> dict[str, Any]:
        data.setdefault(
            "idx",
            await ProjectTaskService.next_assignment_index(ctx.db, data.get("task_id")),
        )
        data.setdefault("assigned_by", ctx.user.id)
        data.setdefault("assigned_at", datetime.utcnow())
        data.setdefault("status", "active")
        data.setdefault("is_active", True)
        return data

    async def after_create(self, record: Any, ctx: Context) -> None:
        await ProjectTaskService.post_create_assignment(record, ctx.db, ctx.user)
        await super().after_create(record, ctx)


register_entity_api("project", ProjectAPI())
register_entity_api("project_member", ProjectMemberAPI())
register_entity_api("task_type", TaskTypeAPI())
register_entity_api("task_category", AuditedEntityAPI())
register_entity_api("task", TaskAPI())
register_entity_api("task_assignment", TaskAssignmentAPI())
register_entity_api("task_link", AuditedEntityAPI())
