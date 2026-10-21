"""
RBAC Application Service (CLEAN Architecture - Application Layer)
=================================================================
This is the PROPER CLEAN ARCHITECTURE implementation for RBAC.

ARCHITECTURE LAYERS:
-------------------
1. Domain Layer: Core business rules and entities (User, Role, EntityPermission)
2. Application Layer (THIS FILE): Orchestrates business logic, delegates to repositories
3. Infrastructure Layer: Database access, caching, external services
4. Interface Layer (API): FastAPI routes, HTTP handlers

CLEAN ARCHITECTURE PRINCIPLES:
------------------------------
- Dependency Inversion: Depends on abstractions (repository interfaces), not concrete implementations
- Dependency Injection: Receives dependencies via constructor, not creating them internally
- No Infrastructure Coupling: No imports of AsyncSession, cache, or DB models
- Single Responsibility: Only orchestrates business logic, delegates data access

MIGRATION STATUS:
-----------------
This is the TARGET implementation. The legacy file 'rbac.py' violates CLEAN architecture
by using static methods, direct DB access, and infrastructure coupling.

Migrate all API routes from:
    from app.application.services.access_control.rbac import RBACService
    RBACService.check_permission_async(db, user, entity, action)

To:
    from app.api.dependencies import get_rbac_service
    rbac: RBACAppService = Depends(get_rbac_service)
    await rbac.check_permission(user_id, entity, action, role_ids, is_superuser)

USAGE:
------
Constructor injection:
    rbac = RBACAppService(auth_repo)

Check permission:
    await rbac.check_permission(
        user_id=user.id,
        entity="work_order",
        action="read",
        role_ids=user.role_ids,
        is_superuser=user.is_superuser
    )
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from app.core.constants.permissions import (
    ROW_SCOPE_ALL,
    ROW_SCOPE_OWNER_ONLY,
    merge_scope,
    PERMISSION_FLAGS,
)
from app.domain.protocols.permission_repository import PermissionRepositoryProtocol


# Valid entity-level actions that map to a `can_{action}` flag.
VALID_ACTIONS = frozenset(
    flag.replace("can_", "") for flag in PERMISSION_FLAGS if flag.startswith("can_")
)
SYSTEM_ADMIN_ENTITIES = frozenset(
    {
        "user",
        "role",
        "entity_permission",
        "audit_log",
        "oc_audit_log",
        "ledger",
        "model",
        "model_definition",
        "entity_definition",
        "api_key",
        "error_log",
        "user_session",
        "workflow",
        "workflow_state",
        "workflow_action",
        "workflow_state_link",
        "workflow_transition",
        "module_order",
        "entity_order",
        "payroll_line_item",
        "payroll_period",
        "payroll_entry",
        "invoice",
        "payroll_settings",
        "user_task_rate",
    }
)


def is_system_admin_entity(entity: str) -> bool:
    return entity in SYSTEM_ADMIN_ENTITIES


class InvalidPermissionAction(ValueError):
    """Raised when an unrecognized action is supplied to `check_permission`."""


@dataclass
class EffectivePermission:
    """Typed merged permission view for a single entity.

    Avoids raw dicts with hardcoded string keys and provides a single
    ``to_dict`` conversion point for API responses.
    """

    can_read: bool = False
    can_create: bool = False
    can_update: bool = False
    can_delete: bool = False
    can_select: bool = False
    can_export: bool = False
    can_import: bool = False
    in_sidebar: bool = False
    row_scope: list[str] = field(default_factory=list)

    def has_action(self, action: str) -> bool:
        """Return the value of the ``can_{action}`` flag if it exists."""
        return bool(getattr(self, f"can_{action}", False))

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dict representation."""
        return {
            "can_read": self.can_read,
            "can_create": self.can_create,
            "can_update": self.can_update,
            "can_delete": self.can_delete,
            "can_select": self.can_select,
            "can_export": self.can_export,
            "can_import": self.can_import,
            "in_sidebar": self.in_sidebar,
            "row_scope": list(self.row_scope),
        }


class RBACAppService:
    """Application-layer RBAC that delegates to a permission repository."""

    def __init__(self, auth_repo: PermissionRepositoryProtocol):
        self.auth_repo = auth_repo

    async def check_permission(
        self,
        user_id: str,
        entity: str,
        action: str,
        role_ids: Optional[list[str]] = None,
        is_superuser: bool = False,
    ) -> bool:
        if is_superuser:
            return True

        if not role_ids:
            return False

        if action not in VALID_ACTIONS:
            raise InvalidPermissionAction(
                f"Invalid permission action '{action}'. Valid actions: {sorted(VALID_ACTIONS)}"
            )

        if is_system_admin_entity(entity) and not await self._has_system_admin_role(
            role_ids
        ):
            return False

        perms = await self.get_effective_permissions(role_ids, entity)
        entity_perms = perms.get(entity)
        if not entity_perms:
            return False

        return entity_perms.has_action(action)

    async def get_effective_permissions(
        self,
        role_ids: list[str],
        entity_name: Optional[str] = None,
    ) -> dict[str, EffectivePermission]:
        """Return merged permissions per entity for the given roles."""
        if not role_ids:
            return {}

        is_system_admin = await self._has_system_admin_role(role_ids)
        if not is_system_admin:
            if entity_name and is_system_admin_entity(entity_name):
                return {}

        permissions = await self.auth_repo.get_permissions_for_user_roles(role_ids)

        result: dict[str, EffectivePermission] = {}
        for perm in permissions:
            name = perm.entity_name
            if is_system_admin_entity(name) and not is_system_admin:
                continue
            if entity_name and name != entity_name:
                continue

            current = result.setdefault(name, EffectivePermission())

            for flag in PERMISSION_FLAGS:
                if getattr(perm, flag, False):
                    setattr(current, flag, True)
            current.row_scope = merge_scope(current.row_scope, perm.row_scope)

        return result

    async def _has_system_admin_role(self, role_ids: list[str]) -> bool:
        role_lookup = getattr(self.auth_repo, "get_role_names", None)
        if role_lookup is None:
            return False
        role_names = await role_lookup(role_ids)
        return bool({"SystemManager", "Administrator"}.intersection(role_names))

    async def get_row_scope(self, role_ids: list[str], entity_name: str) -> list[str]:
        """Return the combined row scope filters for an entity across all roles.

        Fails closed for unknown entities: an entity with no permission row
        defaults to ``owner_only`` instead of ``all``. This is safer because a
        missing permission record should never silently grant broad visibility.
        """
        perms = await self.get_effective_permissions(role_ids, entity_name)
        entity_perms = perms.get(entity_name)
        if not entity_perms:
            return [ROW_SCOPE_OWNER_ONLY]

        return entity_perms.row_scope or [ROW_SCOPE_ALL]
