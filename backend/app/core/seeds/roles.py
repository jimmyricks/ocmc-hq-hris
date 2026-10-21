"""
Seed: Roles
===========
Creates the three default system roles.
Idempotent — skips existing roles by name.
"""
import bcrypt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.seeds import SeedResult
from app.core.framework.models.auth import Role

# Canonical role definitions
ROLES = [
    {
        "name": "SystemManager",
        "description": "Full system access — can manage everything including users, roles, and admin settings.",
        "is_active": True,
    },
    {
        "name": "Administrator",
        "description": "System administrator with full platform administration access.",
        "is_active": True,
    },
    {
        "name": "ProjectManager",
        "description": "Workspace supervisor responsible for projects and task coordination.",
        "is_active": True,
    },
    {
        "name": "Employee",
        "description": "Workspace member who can view relevant work and submit assigned tasks.",
        "is_active": True,
    },
    {
        "name": "HR",
        "description": "Global read-only directory and controlled payroll operations.",
        "is_active": True,
    },
    {
        "name": "Technician",
        "description": "CRUD access to operational modules. No administrative access.",
        "is_active": True,
    },
    {
        "name": "Viewer",
        "description": "Read-only access across all modules. Cannot create, update, or delete records.",
        "is_active": True,
    },
]


async def seed_roles(db: AsyncSession) -> SeedResult:
    """Create default roles. Skips roles that already exist by name."""
    result = SeedResult(entity="Role")

    for role_def in ROLES:
        existing = await db.execute(select(Role).where(Role.name == role_def["name"]))
        if existing.scalar_one_or_none():
            result.skipped += 1
            continue

        db.add(Role(**role_def))
        result.created += 1

    await db.commit()
    return result
