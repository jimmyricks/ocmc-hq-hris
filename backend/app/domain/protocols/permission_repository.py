"""
Permission Repository Protocol
==============================
Minimal abstraction for permission lookup used by the RBAC application service.

This keeps the application layer decoupled from the concrete SQLAlchemy
`AuthRepository` implementation while still allowing it to be injected.
"""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class PermissionRepositoryProtocol(Protocol):
    """Interface for reading role/entity permissions."""

    async def get_permissions_for_user_roles(
        self,
        role_ids: list[str],
    ) -> list[Any]:
        """Fetch all entity permissions for the supplied role IDs."""
        ...

    async def get_role_names(self, role_ids: list[str]) -> list[str]:
        """Fetch role names for the supplied role IDs."""
        ...
