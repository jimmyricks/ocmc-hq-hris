from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Any, Optional
from app.meta.registry import MetaRegistry
from app.core.database import get_db
from app.core.security import get_current_user_from_token, CurrentUser
from app.core.framework.models.auth import EntityPermission
from app.core.framework.models.ordering import ModuleOrder, EntityOrder
from app.core.constants.permissions import ROW_SCOPE_ALL, PERMISSION_FLAGS, merge_scope

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


@router.post("/reload", name="reload_meta")
async def reload_meta(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """Reload all entity metadata into the registry.

    Superuser-only helper for development: uvicorn does not watch entity
    JSON files, so hand-edited UI config needs an explicit reload (model
    changes still require a process restart, same as before).
    """
    user: CurrentUser = await get_current_user_from_token(authorization, db)
    if not (user.is_superuser or "SystemManager" in (user.roles or [])):
        raise HTTPException(status_code=403, detail="Superuser access required")

    from app.entities import reload_all_entities

    count = reload_all_entities()
    return {
        "status": "success",
        "data": {"entity_count": count},
    }
