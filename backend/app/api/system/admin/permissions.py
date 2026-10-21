"""
Permissions Router
==================
Entity permission management endpoints.
"""
from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import (
    get_current_user_from_token,
    CurrentUser,
    is_system_admin_user,
)
from app.core.framework.models.auth import User, Role, EntityPermission
from app.core.constants.permissions import (
    ROW_SCOPE_ALL,
    PERMISSION_FLAGS,
)
from app.meta.registry import MetaRegistry
from app.schemas.base import ActionResponse
from .common import api_response


def _permission_to_dict(perm: EntityPermission | None, is_system_manager: bool = False) -> dict[str, Any]:
    """Convert an EntityPermission row (or None) into the canonical per-entity dict."""
    if is_system_manager:
        return {
            "can_read": True,
            "can_create": True,
            "can_update": True,
            "can_delete": True,
            "can_select": True,
            "can_export": True,
            "can_import": True,
            "in_sidebar": True,
            "row_scope": ROW_SCOPE_ALL,
        }
    if not perm:
        return {
            "can_read": False,
            "can_create": False,
            "can_update": False,
            "can_delete": False,
            "can_select": False,
            "can_export": False,
            "can_import": False,
            "in_sidebar": False,
            "row_scope": ROW_SCOPE_ALL,
        }
    return {
        "can_read": perm.can_read,
        "can_create": perm.can_create,
        "can_update": perm.can_update,
        "can_delete": perm.can_delete,
        "can_select": perm.can_select,
        "can_export": perm.can_export,
        "can_import": perm.can_import,
        "in_sidebar": perm.in_sidebar,
        "row_scope": perm.row_scope or ROW_SCOPE_ALL,
    }


def _compact_to_entities(compact: dict[str, Any], all_entities: list[str]) -> dict[str, dict[str, Any]]:
    """Convert the legacy compact {can_read: [entity...]} format into canonical entities."""
    entities: dict[str, dict[str, Any]] = {}
    for entity_name in all_entities:
        perms = {
            flag: entity_name in set(compact.get(flag, []) or [])
            for flag in PERMISSION_FLAGS
        }
        perms["row_scope"] = compact.get("row_scope", {}).get(entity_name, ROW_SCOPE_ALL)
        entities[entity_name] = perms
    return entities


def _entities_to_compact(entities: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Convert canonical entities into the legacy compact {can_read: [entity...]} format."""
    compact: dict[str, Any] = {flag: [] for flag in PERMISSION_FLAGS}
    for entity_name, perms in entities.items():
        for flag in PERMISSION_FLAGS:
            if perms.get(flag):
                compact[flag].append(entity_name)
    return compact


def _normalize_entities_input(permissions: Any, all_entities: list[str]) -> dict[str, dict[str, Any]]:
    """Parse any supported permissions input into the canonical entities dict."""
    if not isinstance(permissions, dict):
        return {}

    # New canonical format: permissions.entities = { entity: { can_read: bool, row_scope: str } }
    if "entities" in permissions:
        entities = permissions["entities"]
        return {
            entity_name: {
                flag: perm_data.get(flag, False) if isinstance(perm_data, dict) else False
                for flag in PERMISSION_FLAGS
            }
            | {"row_scope": perm_data.get("row_scope", ROW_SCOPE_ALL) if isinstance(perm_data, dict) else ROW_SCOPE_ALL}
            for entity_name, perm_data in entities.items()
        }

    # Legacy compact format: { can_read: [entity...], can_create: [entity...], ... }
    if any(k in permissions for k in PERMISSION_FLAGS):
        return _compact_to_entities(permissions, all_entities)

    # Legacy entity-keyed map: { entity: { can_read: bool, ... } }
    return {
        entity_name: {
            flag: perm_data.get(flag, False) if isinstance(perm_data, dict) else False
            for flag in PERMISSION_FLAGS
        }
        | {"row_scope": perm_data.get("row_scope", ROW_SCOPE_ALL) if isinstance(perm_data, dict) else ROW_SCOPE_ALL}
        for entity_name, perm_data in permissions.items()
    }

router = APIRouter(tags=["admin-permissions"])


@router.get("/permissions/entities")
async def get_entities_by_module(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user_from_token)
):
    """Get all entities grouped by module for permission management."""
    if not is_system_admin_user(current_user):
        raise HTTPException(status_code=403, detail="Access denied")
    
    from app.core.framework.models.ordering import ModuleOrder, EntityOrder
    
    entities = MetaRegistry.list_all()
    
    module_orders_result = await db.execute(select(ModuleOrder))
    module_orders = {mo.module_name: mo.sort_order for mo in module_orders_result.scalars().all()}
    
    entity_orders_result = await db.execute(select(EntityOrder))
    entity_orders = {eo.entity_name: eo.sort_order for eo in entity_orders_result.scalars().all()}
    
    rows = []
    for entity in entities:
        module = entity.module or "Other"
        entity_payload = {
            "name": entity.name,
            "label": entity.label,
            "module": module,
            "sort_order": entity_orders.get(entity.name, 999),
        }
        rows.append(entity_payload)
    
    rows.sort(key=lambda e: (module_orders.get(e["module"], 999), e["sort_order"]))
    
    return {
        "status": "success",
        "data": {
            "rows": rows,
            "total_entities": len(entities)
        }
    }


@router.get("/permissions/matrix")
async def get_permission_matrix(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user_from_token)
):
    """Get permission matrix for all roles and entities."""
    if not is_system_admin_user(current_user):
        raise HTTPException(status_code=403, detail="Access denied")
    
    entities = MetaRegistry.list_all()
    entity_names = [e.name for e in entities]
    
    result = await db.execute(
        select(Role).options(selectinload(Role.permissions))
    )
    roles = result.scalars().all()
    
    matrix = []
    for role in roles:
        is_system_manager = role.name in {"SystemManager", "Administrator"}
        role_perms = {p.entity_name: p for p in role.permissions}
        row = {
            "role_id": role.id,
            "role_name": role.name,
            "entities": {}
        }
        for entity_name in entity_names:
            perm = role_perms.get(entity_name)
            row["entities"][entity_name] = _permission_to_dict(perm, is_system_manager)
        matrix.append(row)
    
    return api_response(
        status="success",
        message="Permissions retrieved successfully",
        data={
            "entities": entity_names,
            "matrix": matrix,
        }
    )


@router.get("/permissions/role/{role_id}")
async def get_role_permissions(
    role_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user_from_token)
):
    """Get all permissions for a specific role."""
    if not is_system_admin_user(current_user):
        raise HTTPException(status_code=403, detail="Access denied")
    
    result = await db.execute(
        select(Role).where(Role.id == role_id).options(selectinload(Role.permissions))
    )
    role = result.scalar_one_or_none()
    
    if not role:
        return {"status": "error", "message": "Role not found"}
    
    entities = MetaRegistry.list_all()
    entity_names = [e.name for e in entities]

    is_system_manager = role.name in {"SystemManager", "Administrator"}
    role_perms = {p.entity_name: p for p in role.permissions}

    entities = {
        entity_name: _permission_to_dict(role_perms.get(entity_name), is_system_manager)
        for entity_name in entity_names
    }

    return api_response(
        status="success",
        message="Role permissions retrieved successfully",
        data={
            "role": {
                "id": role.id,
                "name": role.name,
                "description": role.description,
            },
            "permissions": {
                "entities": entities,
                **_entities_to_compact(entities),
            }
        }
    )


@router.put("/permissions/role/{role_id}")
async def update_role_permissions(
    role_id: str,
    permissions_data: dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user_from_token)
):
    """Update all permissions for a specific role."""
    if not is_system_admin_user(current_user):
        raise HTTPException(status_code=403, detail="Access denied")
    
    result = await db.execute(
        select(Role).where(Role.id == role_id)
    )
    role = result.scalar_one_or_none()
    
    if not role:
        return api_response(
            status="error",
            message="Role not found"
        )
    
    if role.name in {"SystemManager", "Administrator"}:
        return api_response(
            status="error",
            message="Cannot modify SystemManager permissions"
        )
    
    # Delete existing permissions
    result = await db.execute(
        select(EntityPermission).where(EntityPermission.role_id == role_id)
    )
    existing_perms = result.scalars().all()
    for perm in existing_perms:
        await db.delete(perm)

    permissions = permissions_data.get("permissions", {})
    all_entities = [e.name for e in MetaRegistry.list_all()]
    entities = _normalize_entities_input(permissions, all_entities)

    for entity_name, perm_data in entities.items():
        if entity_name in ["user", "role", "entity_permission"] and role.name not in {
            "SystemManager",
            "Administrator",
        }:
            continue

        permission = EntityPermission(
            role_id=role_id,
            entity_name=entity_name,
            can_read=perm_data.get("can_read", False),
            can_create=perm_data.get("can_create", False),
            can_update=perm_data.get("can_update", False),
            can_delete=perm_data.get("can_delete", False),
            can_select=perm_data.get("can_select", False),
            can_export=perm_data.get("can_export", False),
            can_import=perm_data.get("can_import", False),
            in_sidebar=perm_data.get("in_sidebar", False),
            row_scope=perm_data.get("row_scope", ROW_SCOPE_ALL),
        )
        db.add(permission)

    await db.commit()

    return api_response(
        status="success",
        message="Permissions updated successfully"
    )


@router.post("/permissions/set")
async def set_permission(
    role_id: str,
    entity_name: str,
    can_read: bool = False,
    can_create: bool = False,
    can_update: bool = False,
    can_delete: bool = False,
    can_select: bool = False,
    can_export: bool = False,
    can_import: bool = False,
    in_sidebar: bool = False,
    row_scope: str = ROW_SCOPE_ALL,
    db: AsyncSession = Depends(get_db),
):
    """Set permission for a role on an entity."""
    result = await db.execute(
        select(EntityPermission)
        .where(EntityPermission.role_id == role_id)
        .where(EntityPermission.entity_name == entity_name)
    )
    perm = result.scalar_one_or_none()

    if perm:
        perm.can_read = can_read
        perm.can_create = can_create
        perm.can_update = can_update
        perm.can_delete = can_delete
        perm.can_select = can_select
        perm.can_export = can_export
        perm.can_import = can_import
        perm.in_sidebar = in_sidebar
        perm.row_scope = row_scope
    else:
        perm = EntityPermission(
            role_id=role_id,
            entity_name=entity_name,
            can_read=can_read,
            can_create=can_create,
            can_update=can_update,
            can_delete=can_delete,
            can_select=can_select,
            can_export=can_export,
            can_import=can_import,
            in_sidebar=in_sidebar,
            row_scope=row_scope,
        )
        db.add(perm)

    await db.commit()
    await db.refresh(perm)

    return api_response(
        status="success",
        message="Permission updated successfully",
        data=_permission_to_dict(perm)
    )


@router.post("/users/permissions/set")
async def set_user_permission(
    user_id: str,
    entity_name: str,
    can_read: bool = False,
    can_create: bool = False,
    can_update: bool = False,
    can_delete: bool = False,
    can_select: bool = False,
    can_export: bool = False,
    can_import: bool = False,
    in_sidebar: bool = False,
    row_scope: str = ROW_SCOPE_ALL,
    db: AsyncSession = Depends(get_db),
):
    """Set permission for a user on an entity by updating their primary role."""
    result = await db.execute(
        select(User).where(User.id == user_id).options(selectinload(User.roles))
    )
    user = result.scalar_one_or_none()

    if not user or not user.roles:
        return ActionResponse(status="error", message="User not found or has no roles")

    primary_role = user.roles[0]

    result = await db.execute(
        select(EntityPermission)
        .where(EntityPermission.role_id == primary_role.id)
        .where(EntityPermission.entity_name == entity_name)
    )
    perm = result.scalar_one_or_none()

    if perm:
        perm.can_read = can_read
        perm.can_create = can_create
        perm.can_update = can_update
        perm.can_delete = can_delete
        perm.can_select = can_select
        perm.can_export = can_export
        perm.can_import = can_import
        perm.in_sidebar = in_sidebar
        perm.row_scope = row_scope
    else:
        perm = EntityPermission(
            role_id=primary_role.id,
            entity_name=entity_name,
            can_read=can_read,
            can_create=can_create,
            can_update=can_update,
            can_delete=can_delete,
            can_select=can_select,
            can_export=can_export,
            can_import=can_import,
            in_sidebar=in_sidebar,
            row_scope=row_scope,
        )
        db.add(perm)

    await db.commit()
    await db.refresh(perm)

    return ActionResponse(
        status="success",
        message="Permission updated",
        data=_permission_to_dict(perm)
    )
