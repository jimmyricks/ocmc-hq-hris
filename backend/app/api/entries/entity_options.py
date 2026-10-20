"""
Entity Options Routes
======================
Options and grouped-options for link field dropdowns.
"""
from typing import Any, Optional
from fastapi import APIRouter, Depends, Query, Header
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, desc
from sqlalchemy.sql.sqltypes import String, Text

from app.core.database import get_db
from app.core.security import get_current_user_from_token, CurrentUser
from app.meta.registry import MetaRegistry
from app.application.services.access_control.rbac_service import RBACAppService
from app.application.services.access_control.row_scope_service import RowScopeService
from app.api.dependencies import get_rbac_service, get_row_scope_service
from app.infrastructure.database.repositories.entity_repository import get_entity_model
from app.infrastructure.database.query.filter_builder import build_filter_condition

router = APIRouter(tags=["entity"])


class QueryOptionsRequest(BaseModel):
    """Request model for query-options endpoint."""
    key: str = Field(..., description="Query key identifier")
    entity: str = Field(..., description="Entity name")
    field: Optional[str] = Field(None, description="Field name")
    form_state: Optional[dict] = Field(None, description="Form state context")
    static_params: Optional[dict] = Field(None, description="Static parameters")


@router.get("/{child_entity}/grouped-options", name="get_grouped_options")
async def get_grouped_options(
    child_entity: str,
    parent_entity: str = Query(...),
    child_parent_fk_field: str = Query(...),
    search: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
    rbac: RBACAppService = Depends(get_rbac_service),
    row_scope_service: RowScopeService = Depends(get_row_scope_service),
):
    """Get options grouped by parent for parent_child_link field type."""
    child_meta = MetaRegistry.get(child_entity)
    parent_meta = MetaRegistry.get(parent_entity)

    if not child_meta:
        return {"status": "error", "message": f"Child entity '{child_entity}' not found"}
    if not parent_meta:
        return {"status": "error", "message": f"Parent entity '{parent_entity}' not found"}

    user = await get_current_user_from_token(authorization, db)
    # Allow access if user has can_select OR can_read permission
    has_select = await rbac.check_permission(
        user_id=user.id,
        entity=child_entity,
        action="select",
        role_ids=user.role_ids,
        is_superuser=user.is_superuser
    )
    has_read = await rbac.check_permission(
        user_id=user.id,
        entity=child_entity,
        action="read",
        role_ids=user.role_ids,
        is_superuser=user.is_superuser
    )
    has_workspace_read = await row_scope_service.can_read_entity(
        child_entity, user.id, user.roles or [], user.is_superuser
    )
    if not has_select and not has_read and not has_workspace_read:
        return {"status": "error", "message": "Permission denied"}

    child_model = get_entity_model(child_entity)
    parent_model = get_entity_model(parent_entity)

    if not child_model or not parent_model:
        return {"status": "error", "message": "Model not found"}

    # Validate child_parent_fk_field exists on child_model
    if not hasattr(child_model, child_parent_fk_field):
        return {"status": "error", "message": f"Field '{child_parent_fk_field}' not found on entity '{child_entity}'"}

    child_value_field = "id"
    child_label_field = child_meta.title_field or "name"
    parent_value_field = "id"
    parent_label_field = parent_meta.title_field or "name"

    query = select(child_model, parent_model).join(
        parent_model,
        getattr(child_model, child_parent_fk_field) == parent_model.id
    )

    if search:
        search_conditions = []
        if hasattr(child_model, child_label_field):
            search_conditions.append(getattr(child_model, child_label_field).ilike(f"%{search}%"))
        if hasattr(parent_model, parent_label_field):
            search_conditions.append(getattr(parent_model, parent_label_field).ilike(f"%{search}%"))
        if search_conditions:
            query = query.where(or_(*search_conditions))

    if hasattr(parent_model, parent_label_field):
        query = query.order_by(getattr(parent_model, parent_label_field))
    if hasattr(child_model, child_label_field):
        query = query.order_by(getattr(child_model, child_label_field))

    query = await row_scope_service.apply_scope_to_query(
        query,
        child_model,
        child_entity,
        str(user.id),
        user.role_ids,
        user.roles or [],
        user.is_superuser,
    )

    query = query.limit(limit)

    result = await db.execute(query)
    rows = result.all()

    groups_dict = {}
    for child_record, parent_record in rows:
        parent_value = getattr(parent_record, parent_value_field, None)
        parent_label = getattr(parent_record, parent_label_field, None) or parent_value
        parent_key = str(parent_value)

        if parent_key not in groups_dict:
            groups_dict[parent_key] = {"label": str(parent_label), "options": []}

        child_value = getattr(child_record, child_value_field, None)
        child_label = getattr(child_record, child_label_field, None) or child_value

        option = {"value": str(child_value), "label": str(child_label)}

        # Add description using child entity's list_view fields
        child_list_view_fields = [field.name for field in child_meta.fields if field.in_list_view and field.name != child_label_field]
        if child_list_view_fields:
            description_parts = []
            for field_name in child_list_view_fields:
                if hasattr(child_record, field_name):
                    field_value = getattr(child_record, field_name)
                    if field_value not in (None, ""):
                        description_parts.append(str(field_value))
            if description_parts:
                option["description"] = " | ".join(description_parts)

        groups_dict[parent_key]["options"].append(option)

    return {"status": "success", "groups": list(groups_dict.values())}


@router.get("/{entity}/options", name="get_entity_options")
async def get_entity_options(
    entity: str,
    search: Optional[str] = Query(None),
    limit: int = Query(5, ge=1, le=500),
    filters: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
    rbac: RBACAppService = Depends(get_rbac_service),
    row_scope_service: RowScopeService = Depends(get_row_scope_service),
):
    """Get options for link field (combo box/select)."""
    meta = MetaRegistry.get(entity)
    if not meta:
        return {"status": "error", "message": f"Entity '{entity}' not found", "options": []}

    user = await get_current_user_from_token(authorization, db)
    # Allow access if user has can_select OR can_read permission
    has_select = await rbac.check_permission(
        user_id=user.id,
        entity=entity,
        action="select",
        role_ids=user.role_ids,
        is_superuser=user.is_superuser
    )
    has_read = await rbac.check_permission(
        user_id=user.id,
        entity=entity,
        action="read",
        role_ids=user.role_ids,
        is_superuser=user.is_superuser
    )
    has_workspace_read = await row_scope_service.can_read_entity(
        entity, user.id, user.roles or [], user.is_superuser
    )
    if not has_select and not has_read and not has_workspace_read:
        return {"status": "error", "message": "Permission denied", "options": []}

    model = get_entity_model(entity)
    if not model:
        return {"status": "error", "message": f"Model for '{entity}' not found", "options": []}

    value_field = meta.naming.field if meta.naming and meta.naming.field else "id"
    label_field = meta.title_field or value_field

    # Validate value_field exists on model
    if not hasattr(model, value_field):
        return {"status": "error", "message": f"Field '{value_field}' not found on entity '{entity}'", "options": []}

    query = select(model)

    if search:
        search_cols = []
        
        # Always search value_field and label_field if they exist and are string/text
        if hasattr(model, value_field):
            col = getattr(model, value_field)
            if isinstance(col.type, (String, Text)):
                search_cols.append(col.ilike(f"%{search}%"))
        if hasattr(model, label_field) and label_field != value_field:
            col = getattr(model, label_field)
            if isinstance(col.type, (String, Text)):
                search_cols.append(col.ilike(f"%{search}%"))
        
        # Also search in entity's search_fields if defined
        if meta.search_fields:
            for field_name in meta.search_fields:
                if hasattr(model, field_name) and field_name not in (value_field, label_field):
                    col = getattr(model, field_name)
                    if isinstance(col.type, (String, Text)):
                        search_cols.append(col.ilike(f"%{search}%"))
        
        if search_cols:
            query = query.where(or_(*search_cols))

    # Default ordering:
    # - If search is empty: show most recently created records first (better UX for lookups)
    # - If search is provided: keep deterministic label ordering
    if not search and hasattr(model, "created_at"):
        query = query.order_by(desc(getattr(model, "created_at")))
    elif hasattr(model, label_field):
        query = query.order_by(getattr(model, label_field))

    # Apply filters (JSON-encoded dict of field_name: value)
    if filters:
        import json
        try:
            filter_dict = json.loads(filters)
            for field_name, field_value in filter_dict.items():
                if not hasattr(model, field_name):
                    continue
                # Validate filter value is safe (scalar or list only, no nested structures)
                if field_value is None:
                    continue
                if isinstance(field_value, (str, int, float, bool)):
                    # Safe scalar value
                    condition = build_filter_condition(getattr(model, field_name), field_value)
                    if condition is not None:
                        query = query.where(condition)
                elif isinstance(field_value, list):
                    # Only allow lists of scalars
                    if all(isinstance(v, (str, int, float, bool)) for v in field_value):
                        condition = build_filter_condition(getattr(model, field_name), field_value)
                        if condition is not None:
                            query = query.where(condition)
                # Reject nested structures (dict, list of lists, etc.)
        except (json.JSONDecodeError, TypeError):
            pass

    query = await row_scope_service.apply_scope_to_query(
        query,
        model,
        entity,
        str(user.id),
        user.role_ids,
        user.roles or [],
        user.is_superuser,
    )

    query = query.limit(limit)

    result = await db.execute(query)
    records = result.scalars().all()

    options = []
    # Use search_fields for description (comma-separated) if defined;
    # otherwise fall back to in_options_description, then in_list_view
    if meta.search_fields:
        desc_fields = [f for f in meta.fields if f.name in meta.search_fields and f.name != label_field]
        use_comma_separator = True
    else:
        desc_fields = [f for f in meta.fields if f.in_options_description and f.name != label_field]
        if not desc_fields:
            desc_fields = [f for f in meta.fields if f.in_list_view and f.name != label_field]
        use_comma_separator = False

    # Precompute label field meta (to detect link labels)
    label_field_meta = next((f for f in meta.fields if f.name == label_field), None)

    # Batch fetch all linked titles to avoid N+1 queries
    # Collect all (link_entity, record_id) pairs that need resolution
    link_fetch_map: dict[str, set[Any]] = {}  # {link_entity: {id1, id2, ...}}

    # First pass: collect all link IDs from label field and description fields
    for record in records:
        # Check label field if it's a link
        if label_field_meta and label_field_meta.link_entity:
            label_raw = getattr(record, label_field, None)
            if label_raw not in (None, ""):
                link_fetch_map.setdefault(label_field_meta.link_entity, set()).add(label_raw)

        # Check description fields if they're links
        if desc_fields:
            for field_meta in desc_fields:
                if field_meta.link_entity:
                    field_value = getattr(record, field_meta.name, None)
                    if field_value not in (None, ""):
                        link_fetch_map.setdefault(field_meta.link_entity, set()).add(field_value)

    # Batch fetch titles for each link entity
    link_title_cache: dict[str, dict[str, str]] = {}  # {link_entity: {id: title}}
    for link_entity, ids_to_fetch in link_fetch_map.items():
        if not ids_to_fetch:
            continue
        link_meta = MetaRegistry.get(link_entity)
        link_model = get_entity_model(link_entity)
        if not link_meta or not link_model:
            # Cache IDs as-is if entity not found
            link_title_cache[link_entity] = {str(id): str(id) for id in ids_to_fetch}
            continue

        title_field = link_meta.title_field or "id"
        result = await db.execute(
            select(link_model.id, getattr(link_model, title_field))
            .where(link_model.id.in_(ids_to_fetch))
        )
        link_title_cache[link_entity] = {
            str(row[0]): str(row[1] or row[0]) for row in result.all()
        }

    # Helper to get title from cache
    def get_link_title(link_entity: str, record_id: Any) -> str:
        if record_id in (None, ""):
            return str(record_id)
        return link_title_cache.get(link_entity, {}).get(str(record_id), str(record_id))

    # Second pass: build options using cached titles
    for record in records:
        value = getattr(record, value_field, None) or getattr(record, "id", None)
        label_raw = getattr(record, label_field, None) or value

        # If the label field itself is a link, resolve to its title_field
        if label_field_meta and label_field_meta.link_entity:
            label_resolved = get_link_title(label_field_meta.link_entity, label_raw)
        else:
            label_resolved = label_raw

        option = {"value": str(value), "label": str(label_resolved)}

        # Add description using list_view fields
        if desc_fields:
            description_parts = []
            for field_meta in desc_fields:
                field_name = field_meta.name
                if hasattr(record, field_name):
                    field_value = getattr(record, field_name)
                    if field_value in (None, ""):
                        continue
                    # If this field is a link, resolve its title_field
                    if field_meta.link_entity:
                        field_value = get_link_title(field_meta.link_entity, field_value)
                    description_parts.append(str(field_value))
            if description_parts:
                separator = ", " if use_comma_separator else " | "
                option["description"] = separator.join(description_parts)

        options.append(option)

    return {"status": "success", "options": options}


@router.post("/query-options", name="post_query_options")
async def post_query_options(
    request: QueryOptionsRequest,
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
    rbac: RBACAppService = Depends(get_rbac_service),
):
    """Execute a whitelisted query for query_link field type."""
    from app.application.services.documents.query_link import execute_query_link

    user = await get_current_user_from_token(authorization, db)

    meta = MetaRegistry.get(request.entity)
    if meta and not await rbac.check_permission(
        user_id=user.id,
        entity=request.entity,
        action="read",
        role_ids=user.role_ids,
        is_superuser=user.is_superuser
    ):
        return {"status": "error", "message": "Permission denied", "options": []}

    result = await execute_query_link(
        key=request.key, db=db, entity=request.entity, field=request.field or "",
        form_state=request.form_state, static_params=request.static_params
    )
    return result
