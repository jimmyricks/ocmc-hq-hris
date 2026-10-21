"""
Admin Router Package
====================
Modular admin endpoints split into focused sub-routers.
"""
from fastapi import APIRouter, Depends

from app.core.security import require_system_admin_user

from . import users, roles, permissions, ordering, sessions, api_keys

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_system_admin_user)],
)

# Include all sub-routers
router.include_router(users.router)
router.include_router(roles.router)
router.include_router(permissions.router)
router.include_router(ordering.router)
router.include_router(sessions.router)
router.include_router(api_keys.router)
