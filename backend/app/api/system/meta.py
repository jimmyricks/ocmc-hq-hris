from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Any, Optional
from app.meta.registry import MetaRegistry
from app.core.database import get_db
from app.core.security import get_current_user_from_token, CurrentUser
from app.core.framework.models.auth import EntityPermission
from app.core.framework.models.ordering import ModuleOrder, EntityOrder
from app.core.constants.permissions import ROW_SCOPE_ALL, PERMISSION_FLAGS, merge_scope
from app.infrastructure.database.repositories.workflow_repository import WorkflowRepository

router = APIRouter(prefix="/meta", tags=["meta"])

MODULE_LABELS = {
    "core": "Core",
}

MODULE_ICONS = {
    "core": "settings",
}

MODULE_ORDER_ALIASES = {}


def _module_order_key(module_name: str | None) -> str:
    if not module_name:
        return "other"
    return MODULE_ORDER_ALIASES.get(module_name, module_name)


def _aggregate_permissions(perms: list[EntityPermission]) -> dict[str, dict[str, Any]]:
    agg: dict[str, dict[str, Any]] = {}
    for perm in perms:
        key = perm.entity_name
        if key not in agg:
            agg[key] = {
                "can_read": False,
                "can_create": False,
                "can_update": False,
                "can_delete": False,
                "can_select": False,
                "can_export": False,
                "can_import": False,
                "in_sidebar": False,
                "row_scope": [],
            }
        entry = agg[key]
        for flag in PERMISSION_FLAGS:
            if getattr(perm, flag, False):
                entry[flag] = True
        entry["row_scope"] = merge_scope(entry["row_scope"], perm.row_scope)
    return agg


@router.get("/modules", name="get_modules")
async def get_modules():
    """Get all module metadata with labels and icons."""
    return {
        "status": "success",
        "data": {
            "labels": MODULE_LABELS,
            "icons": MODULE_ICONS,
        }
    }


@router.get("", name="get_meta_list")
async def get_meta_list(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """List all entities the user has access to."""
    user: CurrentUser = await get_current_user_from_token(authorization, db)
    
    # Get all entities
    entities = MetaRegistry.list_all()
    
    # Get module orders
    module_orders_result = await db.execute(select(ModuleOrder))
    module_orders = {mo.module_name: mo.sort_order for mo in module_orders_result.scalars().all()}
    
    # Get entity orders
    entity_orders_result = await db.execute(select(EntityOrder))
    entity_orders = {eo.entity_name: eo.sort_order for eo in entity_orders_result.scalars().all()}
    
    # If no user or user is not authenticated, return empty list
    if not user or user.username == "anonymous":
        return {
            "status": "success", 
            "data": []
        }
    
    # If user is SystemManager, return all entities
    if user.is_superuser:
        entity_list = [
            {
                "name": e.name,
                "label": e.label,
                "module": e.module,
                "group": e.group,
                "icon": e.icon,
                "in_sidebar": e.in_sidebar,
                "is_child_table": e.is_child_table,
                "permissions": {
                    "can_read": True,
                    "can_create": True,
                    "can_update": True,
                    "can_delete": True,
                    "can_select": True,
                    "can_export": True,
                    "can_import": True,
                    "in_sidebar": e.in_sidebar,
                    "row_scope": [ROW_SCOPE_ALL],
                },
                "_module_order": module_orders.get(_module_order_key(e.module), 999),
                "_entity_order": entity_orders.get(e.name, 999),
            }
            for e in entities
        ]
        # Sort by module order, then entity order
        entity_list.sort(key=lambda x: (x["_module_order"], x["_entity_order"]))
        # Remove temporary sort fields
        for e in entity_list:
            del e["_module_order"]
            del e["_entity_order"]
        
        return {
            "status": "success",
            "data": entity_list
        }

    role_ids = user.role_ids

    # Fetch all permissions for user's roles
    result = await db.execute(
        select(EntityPermission)
        .where(EntityPermission.role_id.in_(role_ids))
    )
    permissions = result.scalars().all()
    perms_by_entity = _aggregate_permissions(permissions)

    filtered_entities = []
    for e in entities:
        perms = perms_by_entity.get(
            e.name,
            {
                "can_read": False,
                "can_create": False,
                "can_update": False,
                "can_delete": False,
                "can_select": False,
                "can_export": False,
                "can_import": False,
                "in_sidebar": False,
                "row_scope": [ROW_SCOPE_ALL],
            },
        )
        # Only include entities the user can read AND has permission to show in sidebar
        if not perms["can_read"] or not perms["in_sidebar"]:
            continue
        filtered_entities.append(
            {
                "name": e.name,
                "label": e.label,
                "module": e.module,
                "group": e.group,
                "icon": e.icon,
                "in_sidebar": perms["in_sidebar"],
                "is_child_table": e.is_child_table,
                "permissions": {
                    "can_read": perms["can_read"],
                    "can_create": perms["can_create"],
                    "can_update": perms["can_update"],
                    "can_delete": perms["can_delete"],
                    "can_select": perms["can_select"],
                    "can_export": perms["can_export"],
                    "can_import": perms["can_import"],
                    "in_sidebar": perms["in_sidebar"],
                    "row_scope": perms["row_scope"],
                },
                "_module_order": module_orders.get(_module_order_key(e.module), 999),
                "_entity_order": entity_orders.get(e.name, 999),
            }
        )
    
    # Sort by module order, then entity order
    filtered_entities.sort(key=lambda x: (x["_module_order"], x["_entity_order"]))
    # Remove temporary sort fields
    for e in filtered_entities:
        del e["_module_order"]
        del e["_entity_order"]

    return {
        "status": "success",
        "data": filtered_entities,
    }


@router.get("/{entity}", name="get_meta_detail")
async def get_meta_detail(
    entity: str,
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """Get Svelte-optimized metadata for a specific entity."""
    from app.core.exceptions import ForbiddenError

    meta = MetaRegistry.get(entity)
    if not meta:
        return {
            "status": "error",
            "message": f"Entity '{entity}' not found",
        }

    user: CurrentUser = await get_current_user_from_token(authorization, db)

    # Default permissions (superuser / SystemManager)
    permissions = {
        "can_read": True,
        "can_create": True,
        "can_update": True,
        "can_delete": True,
        "can_select": True,
        "can_export": True,
        "can_import": True,
        "in_sidebar": True,
        "row_scope": [ROW_SCOPE_ALL],
    }

    # Aggregated permissions for ALL entities the user has access to
    # (needed for link field permissions)
    all_perms_by_entity: dict[str, dict[str, Any]] = {}

    if user and not user.is_superuser:
        role_ids = user.role_ids
        result = await db.execute(
            select(EntityPermission)
            .where(EntityPermission.role_id.in_(role_ids))
        )
        all_perms = result.scalars().all()
        all_perms_by_entity = _aggregate_permissions(all_perms)

        entity_perms = all_perms_by_entity.get(entity)
        if entity_perms:
            permissions = {
                "can_read": entity_perms.get("can_read", False),
                "can_create": entity_perms.get("can_create", False),
                "can_update": entity_perms.get("can_update", False),
                "can_delete": entity_perms.get("can_delete", False),
                "can_select": entity_perms.get("can_select", False),
                "can_export": entity_perms.get("can_export", False),
                "can_import": entity_perms.get("can_import", False),
                "in_sidebar": entity_perms.get("in_sidebar", False),
                "row_scope": entity_perms.get("row_scope", [ROW_SCOPE_ALL]),
            }
        else:
            permissions = {
                "can_read": False,
                "can_create": False,
                "can_update": False,
                "can_delete": False,
                "can_select": False,
                "can_export": False,
                "can_import": False,
                "in_sidebar": False,
                "row_scope": [ROW_SCOPE_ALL],
            }

    # If user cannot read this entity, return 403
    if not permissions["can_read"] and entity != "user":
        raise ForbiddenError(f"You don't have permission to access {meta.label}")

    # Build link_permissions map for link fields (can_read, can_select per linked entity)
    link_field_permissions: dict[str, dict[str, Any]] = {}
    if meta.fields:
        for field in meta.fields:
            link_entity = getattr(field, 'link_entity', None) or getattr(field, 'child_entity', None)
            if not link_entity or link_entity in link_field_permissions:
                continue
            if user and user.is_superuser:
                link_field_permissions[link_entity] = {
                    "can_read": True,
                    "can_select": True,
                    "can_create": True,
                    "row_scope": [ROW_SCOPE_ALL],
                }
            else:
                lp = all_perms_by_entity.get(link_entity, {})
                link_field_permissions[link_entity] = {
                    "can_read": lp.get("can_read", False),
                    "can_select": lp.get("can_select", False) or lp.get("can_read", False),
                    "can_create": lp.get("can_create", False),
                    "row_scope": lp.get("row_scope", [ROW_SCOPE_ALL]),
                }

    # Svelte-optimized payload: flat, table-ready metadata
    data = MetaRegistry.to_svelte_dict(meta)
    data["link_field_permissions"] = link_field_permissions

    return {
        "status": "success",
        "data": data,
    }
