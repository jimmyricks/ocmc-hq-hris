"""
Utils per-entity API hooks.

Registers audited lifecycle hooks for the short-link and QR-code entities
and attaches them to the generic entity kernel.
"""
from typing import Any

from app.application.services.base_entity_api import BaseEntityAPI, Context, register_entity_api
from app.core.serialization import record_to_dict
from app.modules.collaboration_audit.services import AuditLogService


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


class ShortLinkAPI(AuditedEntityAPI):
    """ShortLink business hooks."""


class ShortLinkClickAPI(AuditedEntityAPI):
    """ShortLinkClick audit hooks (append-only child records)."""


class QrCodeAPI(AuditedEntityAPI):
    """QrCode business hooks."""


register_entity_api("short_link", ShortLinkAPI())
register_entity_api("short_link_click", ShortLinkClickAPI())
register_entity_api("qr_code", QrCodeAPI())
