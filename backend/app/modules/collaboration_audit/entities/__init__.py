"""
Collaboration & Audit per-entity API hooks.

Registers the audit-ledger entity APIs used by the generic CRUD layer.
"""
from app.application.services.base_entity_api import BaseEntityAPI, register_entity_api


class ReadOnlyEntityAPI(BaseEntityAPI):
    """Rejects create/update/delete for immutable audit entities."""

    async def validate_create(self, data, ctx):
        return {"_error": "Audit/ledger records are immutable and cannot be created directly."}

    async def validate_update(self, id, data, ctx):
        return {"_error": "Audit/ledger records are immutable and cannot be updated."}

    async def validate_delete(self, record, ctx):
        return {"_error": "Audit/ledger records are immutable and cannot be deleted."}

    async def before_delete(self, record, ctx):
        from app.core.exceptions import ForbiddenError
        raise ForbiddenError("Audit/ledger records are immutable and cannot be deleted.")


class OcAuditLogAPI(ReadOnlyEntityAPI):
    """OcAuditLog is immutable."""


class LedgerAPI(ReadOnlyEntityAPI):
    """Ledger is immutable."""


register_entity_api("oc_audit_log", OcAuditLogAPI())
register_entity_api("ledger", LedgerAPI())
