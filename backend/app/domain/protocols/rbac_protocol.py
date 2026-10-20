"""
RBAC Protocol
==============
Abstract interface for role-based access control.
"""
from typing import Any, Optional, Protocol, runtime_checkable


@runtime_checkable
class RBACProtocol(Protocol):
    """Interface for permission checks and merged permission lookups."""

    async def check_permission(
        self,
        user_id: str,
        entity: str,
        action: str,
        role_ids: Optional[list[str]] = None,
        is_superuser: bool = False,
    ) -> bool:
        """Check if a user has permission to perform an action on an entity."""
        ...

    async def get_effective_permissions(
        self,
        role_ids: list[str],
        entity_name: Optional[str] = None,
    ) -> dict[str, Any]:
        """Get merged, per-entity permission objects for the given roles."""
        ...

    async def get_row_scope(
        self,
        role_ids: list[str],
        entity_name: str,
    ) -> list[str]:
        """Get the combined row scope filters for an entity across all roles."""
        ...
