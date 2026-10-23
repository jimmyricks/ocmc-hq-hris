"""
Entity CRUD Routes
===================
RESTful Create, Update, Delete operations for entities.

Industry-standard HTTP verbs:
    POST   /{entity}                       # create        -> 201
    PUT    /{entity}/{id}                   # update        -> 200
    DELETE /{entity}/{id}                   # delete        -> 200
    POST   /{entity}/bulk-delete            # bulk delete   -> 200
    POST   /{entity}/actions/{action_name}  # collection-level custom action

Document-level custom actions live in entity_actions.py:
    POST   /{entity}/{id}/action/{action_name}

Thin handlers that delegate to EntityService. The previous single
`POST /{entity}/action` dispatcher (which muxed create/update/delete via a
body field) has been removed in favour of proper HTTP semantics.
"""
import uuid
from typing import Any, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, Header
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user_from_token, CurrentUser
from app.core.serialization import record_to_dict
from app.core.exceptions import ForbiddenError, NotFoundError
from app.meta.registry import MetaRegistry
from app.schemas.base import ActionResponse
from app.application.services.access_control.rbac_service import RBACAppService
from app.application.services.access_control.row_scope_service import RowScopeService
from app.api.dependencies import get_db, get_current_user_from_token, get_rbac_service, get_row_scope_service, get_workflow_service, get_naming_service
from app.api.entries.validation_helpers import (
    _humanize_pydantic_error,
    _humanize_field_name,
    _build_validation_message,
)
from app.application.services.workflows.workflow_service import WorkflowAppService
from app.application.services.documents.link_title_service import get_record_display_name
from app.application.hooks.registry import hook_registry
from app.application.hooks.context import SaveContext
from app.application.services.documents.server_actions import server_actions, ActionContext
from app.application.services.notifications.socketio import socket_manager
from app.application.services.documents.naming_service import NamingAppService
from app.application.services.base_entity_api import Context, get_entity_api
from app.infrastructure.database.repositories.entity_repository import (
    EntityRepository,
    get_entity_model,
)
from app.core.sanitization import sanitize_dict
from app.api.entries.entity_children import BulkChildRequest, bulk_save_children


class CreateEntityRequest(BaseModel):
    data: dict[str, Any]
    children: Optional[dict[str, dict[str, Any]]] = None  # { child_entity: { rows: [], deleted_ids: [] } }


class UpdateEntityRequest(BaseModel):
    data: dict[str, Any]
    children: Optional[dict[str, dict[str, Any]]] = None  # { child_entity: { rows: [], deleted_ids: [] } }


class BulkDeleteRequest(BaseModel):
    ids: list[str]


class CollectionActionRequest(BaseModel):
    payload: Optional[dict[str, Any]] = None


router = APIRouter(tags=["entity"])


def get_entity_repository(db: AsyncSession) -> EntityRepository:
    return EntityRepository(db)


def _get_actor_id(user: CurrentUser) -> str | None:
    return None if user.id == "anonymous" else user.id


def _coerce_incoming_types(model: Any, data: dict[str, Any]) -> dict[str, Any]:
    from app.application.services.entity_service import EntityService
    return EntityService.coerce_incoming_types(model, data)


def _transform_date_range_fields(meta: Any, data: dict[str, Any]) -> dict[str, Any]:
    """
    Transform date_range virtual fields into their physical column equivalents.
    
    If data contains a 'date_range' field with {date_range_start, date_range_end},
    extract those values and add them directly to the data dict, then remove the virtual field.
    """
    result = data.copy()
    
    for field in (meta.fields or []):
        if field.field_type == "date_range" and field.name in result:
            date_range_value = result[field.name]
            if isinstance(date_range_value, dict):
                # Extract start and end from the date_range object
                start_field = f"{field.name}_start"
                end_field = f"{field.name}_end"
                
                if start_field in date_range_value:
                    result[start_field] = date_range_value[start_field]
                if end_field in date_range_value:
                    result[end_field] = date_range_value[end_field]
                
                # Remove the virtual field
                del result[field.name]
    
    return result


def _transform_date_range_fields_reverse(meta: Any, data: dict[str, Any]) -> dict[str, Any]:
    """
    Transform physical date_range columns back into virtual field format.
    
    If data contains date_range_start and date_range_end columns,
    combine them into a single date_range object with {date_range_start, date_range_end}.
    """
    result = data.copy()
    
    for field in (meta.fields or []):
        if field.field_type == "date_range":
            start_field = f"{field.name}_start"
            end_field = f"{field.name}_end"
            
            # If both start and end exist in the data, combine them
            if start_field in result or end_field in result:
                result[field.name] = {
                    "date_range_start": result.get(start_field),
                    "date_range_end": result.get(end_field)
                }
                # Remove the physical columns from the response
                if start_field in result:
                    del result[start_field]
                if end_field in result:
                    del result[end_field]
    
    return result


def _validate_schema(entity: str, meta: Any, data: dict[str, Any], action: str = "create") -> dict[str, str]:
    """
    Validate *data* against the generated Pydantic write schema for *entity*.

    Falls back to a manual required-field scan when no schema is registered
    (e.g. core system entities that skip schema generation).

    Returns a dict of {field_name: error_message} — empty means no errors.
    """
    from pydantic import ValidationError as PydanticValidationError

    if action == "update":
        schema = MetaRegistry.get_update_schema(entity) or MetaRegistry.get_write_schema(entity)
    else:
        schema = MetaRegistry.get_write_schema(entity)
    if schema is not None:
        # On update we only validate fields that are present in the schema
        payload = data if action == "create" else {k: v for k, v in data.items() if k in schema.model_fields}
        try:
            schema.model_validate(payload)
            return {}
        except PydanticValidationError as exc:
            errors: dict[str, str] = {}
            for err in exc.errors():
                loc = err.get("loc", ())
                field_name = loc[0] if loc else "unknown"
                # Humanise the field name using meta when possible
                field_meta = next((f for f in (meta.fields or []) if f.name == field_name), None)
                label = _humanize_field_name(field_name, meta)
                is_required = bool(field_meta and field_meta.required)
                errors[str(field_name)] = _humanize_pydantic_error(err, label, is_required)
            return errors

    # ── Fallback: manual required check ─────────────────────────────────────
    errors = {}
    skip_fields = {"id", "created_at", "updated_at", "created_by", "last_modified_by", "workflow_state", "row_no"}
    for f in (meta.fields or []):
        if f.name in skip_fields:
            continue
        if not f.required:
            continue
        if action == "update" and f.name not in data:
            continue
        value = data.get(f.name)
        if value is None or (isinstance(value, str) and value.strip() == ""):
            errors[f.name] = f"{f.label} is required"
    return errors


# ── Response helpers ──────────────────────────────────────────────────────────

def _ok(status_code: int, message: str, data: Any = None) -> JSONResponse:
    """Build a success JSONResponse with an ActionResponse-shaped body."""
    return JSONResponse(
        status_code=status_code,
        content=ActionResponse(status="success", message=message, data=data).model_dump(mode="json"),
    )


def _err(status_code: int, message: str, *, errors: Optional[dict[str, str]] = None, data: Any = None) -> JSONResponse:
    """Build an error JSONResponse with an ActionResponse-shaped body."""
    return JSONResponse(
        status_code=status_code,
        content=ActionResponse(status="error", message=message, data=data, errors=errors).model_dump(mode="json"),
    )


async def _resolve_entity(entity: str, authorization: Optional[str], db: AsyncSession):
    """Resolve meta/user/api/model/ctx for an entity, raising NotFoundError if missing.

    Returns (meta, user, api, model, ctx, entity_label).
    """
    meta = MetaRegistry.get(entity)
    if not meta:
        raise NotFoundError("Entity", entity)

    user = await get_current_user_from_token(authorization, db)
    api = get_entity_api(entity)
    model = get_entity_model(entity)
    if not model:
        raise NotFoundError("Model", entity)

    ctx = Context(db=db, user=user, meta=meta)
    entity_label = meta.label or entity.replace("_", " ").title()
    return meta, user, api, model, ctx, entity_label


# ── Create ────────────────────────────────────────────────────────────────────

async def _create_entity(
    entity: str,
    data: dict[str, Any],
    children: Optional[dict[str, dict[str, Any]]],
    authorization: Optional[str],
    db: AsyncSession,
    rbac: RBACAppService,
    row_scope_service: RowScopeService,
    workflow_service: WorkflowAppService,
    naming_service: NamingAppService,
) -> JSONResponse:
    """Create a single entity record (plus optional nested children) atomically."""
    meta, user, api, model, ctx, entity_label = await _resolve_entity(entity, authorization, db)

    raw_data = sanitize_dict(data or {})
    raw_data = _transform_date_range_fields(meta, raw_data)
    raw_data = await row_scope_service.prepare_create_data(entity, raw_data, user)

    has_permission = await rbac.check_permission(
        user_id=user.id,
        entity=entity,
        action="create",
        role_ids=user.role_ids,
        is_superuser=user.is_superuser,
    )
    workspace_writes = {
        "project",
        "project_member",
        "task",
        "task_link",
        "task_type",
        "department",
        "planner_event",
        "schedule_series",
        "workspace_resource",
        "resource_booking",
    }
    from app.modules.workspaces.services import WorkspaceService

    if not has_permission and (
        entity not in workspace_writes
        or WorkspaceService.is_admin(user.roles, user.is_superuser)
    ):
        raise ForbiddenError(f"You don't have permission to create {meta.label}")

    req_errors = _validate_schema(entity, meta, raw_data, "create")
    if req_errors:
        return _err(422, _build_validation_message(req_errors, meta), errors=req_errors)

    errors = await api.validate_create(raw_data, ctx)
    if errors:
        return _err(422, _build_validation_message(errors, meta), errors=errors)

    data = await api.before_create(raw_data, ctx)

    save_ctx = SaveContext(db=db, user=user, entity=entity, action="create", meta=meta)
    hook_result = await hook_registry.execute_before_save(entity, data, save_ctx)
    if hook_result and isinstance(hook_result, dict) and "errors" in hook_result:
        return _err(422, _build_validation_message(hook_result["errors"], meta), errors=hook_result["errors"])
    elif hook_result and isinstance(hook_result, dict) and "data" in hook_result:
        data = hook_result["data"]

    data = await row_scope_service.prepare_create_data(entity, data, user)

    if not data.get("id"):
        if meta.naming and meta.naming.enabled:
            generated_id = await naming_service.generate_id(meta.naming, entity)
            if generated_id:
                data["id"] = generated_id
        else:
            data["id"] = str(uuid.uuid4())

    # Auto-fill workflow_state from entity metadata when not provided
    if meta.workflow and meta.workflow.enabled and data.get("workflow_state") in (None, ""):
        try:
            initial_state = await workflow_service.get_initial_state(
                entity, workspace_id=data.get("workspace_id")
            )
            if initial_state:
                data["workflow_state"] = initial_state
        except Exception:
            pass
        if not data.get("workflow_state") and meta.workflow.initial_state:
            data["workflow_state"] = meta.workflow.initial_state

    # If workflow is disabled in JSON but the table enforces NOT NULL on workflow_state,
    # fall back to DB workflow initial state when available.
    if data.get("workflow_state") in (None, "") and hasattr(model, "workflow_state"):
        try:
            initial_state = await workflow_service.get_initial_state(
                entity, workspace_id=data.get("workspace_id")
            )
            if initial_state:
                data["workflow_state"] = initial_state
        except Exception:
            pass

    actor_id = _get_actor_id(user)
    if hasattr(model, "created_by"):
        data["created_by"] = actor_id
    if hasattr(model, "last_modified_by"):
        data["last_modified_by"] = actor_id

    data = _coerce_incoming_types(model, data)

    # Filter out keys that don't map to model columns (prevents TypeError on
    # model(**data) when the frontend sends fields not in the entity definition).
    valid_keys = {c.name for c in model.__table__.columns}
    data = {k: v for k, v in data.items() if k in valid_keys}

    record = model(**data)
    db.add(record)

    try:
        await db.commit()
        await db.refresh(record)
    except Exception as e:
        await db.rollback()
        from sqlalchemy.exc import IntegrityError
        if isinstance(e, IntegrityError):
            return _err(409, "Database integrity error", errors={"type": type(e).__name__, "error": str(e)})
        raise

    await api.after_create(record, ctx)
    hook_result = await hook_registry.execute_after_save(entity, record, save_ctx)

    record_dict = record_to_dict(record)
    record_dict = _transform_date_range_fields_reverse(meta, record_dict)

    # Save children atomically if provided
    if children:
        parent_id = record_dict.get("id")
        if parent_id:
            for child_entity, child_data in children.items():
                bulk_req = BulkChildRequest(
                    rows=child_data.get("rows", []),
                    deleted_ids=child_data.get("deleted_ids", []),
                )
                child_result = await bulk_save_children(
                    entity, parent_id, child_entity, bulk_req, authorization, db,
                    rbac, workflow_service, naming_service, row_scope_service,
                )
                if child_result.status != "success":
                    await db.rollback()
                    return JSONResponse(
                        status_code=400,
                        content=child_result.model_dump(mode="json"),
                    )

    await socket_manager.emit_created(entity, record_dict)
    await socket_manager.emit_post_save(entity, record_dict, "create", hook_result)

    created_label = await get_record_display_name(entity, record_dict, db)
    return _ok(
        201,
        f"{entity_label} {created_label or (record_dict.get('id') or 'unknown')} created",
        data=record_dict,
    )


# ── Update ────────────────────────────────────────────────────────────────────

async def _update_entity(
    entity: str,
    record_id: str,
    data: dict[str, Any],
    children: Optional[dict[str, dict[str, Any]]],
    authorization: Optional[str],
    db: AsyncSession,
    rbac: RBACAppService,
    row_scope_service: RowScopeService,
    workflow_service: WorkflowAppService,
    naming_service: NamingAppService,
) -> JSONResponse:
    """Update a single entity record (plus optional nested children) atomically."""
    meta, user, api, model, ctx, entity_label = await _resolve_entity(entity, authorization, db)

    has_permission = await rbac.check_permission(
        user_id=user.id,
        entity=entity,
        action="update",
        role_ids=user.role_ids,
        is_superuser=user.is_superuser,
    )

    if meta.is_immutable:
        return _err(403, f"{meta.label} records are immutable and cannot be updated")

    repo = EntityRepository(db)
    record = await repo.get_by_id(entity, record_id)
    if not record:
        raise NotFoundError(meta.label, record_id)

    if not await row_scope_service.can_access_record(
        record, entity, str(user.id), user.role_ids, user.roles or [], user.is_superuser,
    ):
        raise ForbiddenError(f"You don't have permission to update this {meta.label}")
    if not has_permission and not row_scope_service._is_workspace_entity(
        entity, record.__class__
    ):
        raise ForbiddenError(f"You don't have permission to update {meta.label}")

    raw_data = sanitize_dict(data or {})
    raw_data = _transform_date_range_fields(meta, raw_data)

    req_errors = _validate_schema(entity, meta, raw_data, "update")
    if req_errors:
        return _err(422, _build_validation_message(req_errors, meta), errors=req_errors)

    errors = await api.validate_update(record_id, raw_data, ctx)
    if errors:
        return _err(422, _build_validation_message(errors, meta), errors=errors)

    data = await api.before_update(record, raw_data, ctx)

    save_ctx = SaveContext(db=db, user=user, entity=entity, action="update", meta=meta)
    hook_result = await hook_registry.execute_before_save(entity, data, save_ctx)
    if hook_result and isinstance(hook_result, dict) and "errors" in hook_result:
        return _err(422, _build_validation_message(hook_result["errors"], meta), errors=hook_result["errors"])
    elif hook_result and isinstance(hook_result, dict) and "data" in hook_result:
        data = hook_result["data"]

    await row_scope_service.authorize_record_write(entity, record, data, user)

    data = _coerce_incoming_types(model, data)

    system_fields = {"id", "created_at", "updated_at", "created_by"}
    for key, value in data.items():
        if key in system_fields:
            continue
        if hasattr(record, key):
            setattr(record, key, value)

    if hasattr(record, "last_modified_by"):
        record.last_modified_by = _get_actor_id(user)

    try:
        await db.commit()
        await db.refresh(record)
    except Exception as e:
        await db.rollback()
        from sqlalchemy.exc import IntegrityError
        if isinstance(e, IntegrityError):
            return _err(409, "Database integrity error", errors={"type": type(e).__name__, "error": str(e)})
        raise

    await api.after_update(record, ctx)
    hook_result = await hook_registry.execute_after_save(entity, record, save_ctx)
    await db.commit()

    # Save children atomically if provided
    if children:
        for child_entity, child_data in children.items():
            bulk_req = BulkChildRequest(
                rows=child_data.get("rows", []),
                deleted_ids=child_data.get("deleted_ids", []),
            )
            child_result = await bulk_save_children(
                entity, record_id, child_entity, bulk_req, authorization, db,
                rbac, workflow_service, naming_service,
            )
            if child_result.status != "success":
                await db.rollback()
                return JSONResponse(status_code=400, content=child_result.model_dump(mode="json"))

    record_dict = record_to_dict(record)
    record_dict = _transform_date_range_fields_reverse(meta, record_dict)
    await socket_manager.emit_updated(entity, record_dict)
    await socket_manager.emit_post_save(entity, record_dict, "update", hook_result)

    updated_label = await get_record_display_name(entity, record_dict, db)
    return _ok(
        200,
        f"{entity_label} {updated_label or (record_dict.get('id') or record_id or 'unknown')} updated",
        data=record_dict,
    )


@router.post("/{entity}", name="create_entity", status_code=201)
async def create_entity(
    entity: str,
    request: CreateEntityRequest,
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
    rbac: RBACAppService = Depends(get_rbac_service),
    row_scope_service: RowScopeService = Depends(get_row_scope_service),
    workflow_service: WorkflowAppService = Depends(get_workflow_service),
    naming_service: NamingAppService = Depends(get_naming_service),
):
    """Create a new entity record.

    Returns 201 Created on success. Errors use proper HTTP status codes:
    404 (entity not found), 403 (forbidden), 422 (validation), 409 (integrity).
    """
    return await _create_entity(
        entity, request.data, request.children, authorization, db,
        rbac, row_scope_service, workflow_service, naming_service,
    )


@router.put("/{entity}/{id}", name="update_entity")
async def update_entity(
    entity: str,
    id: str,
    request: UpdateEntityRequest,
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
    rbac: RBACAppService = Depends(get_rbac_service),
    row_scope_service: RowScopeService = Depends(get_row_scope_service),
    workflow_service: WorkflowAppService = Depends(get_workflow_service),
    naming_service: NamingAppService = Depends(get_naming_service),
):
    """Update an existing entity record by ID.

    Returns 200 OK on success. Errors use proper HTTP status codes:
    404 (entity/record not found), 403 (forbidden/immutable), 422 (validation),
    409 (integrity).
    """
    return await _update_entity(
        entity, id, request.data, request.children, authorization, db,
        rbac, row_scope_service, workflow_service, naming_service,
    )


@router.post("/{entity}/actions/{action_name}", name="collection_action")
async def collection_action(
    entity: str,
    action_name: str,
    body: Optional[CollectionActionRequest] = None,
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
    rbac: RBACAppService = Depends(get_rbac_service),
    row_scope_service: RowScopeService = Depends(get_row_scope_service),
):
    """Execute a collection-level (id-less) server action on an entity.

    Document-level actions (which require a record id) live at
    POST /{entity}/{id}/action/{action_name} (see entity_actions.py).
    """
    meta = MetaRegistry.get(entity)
    if not meta:
        raise NotFoundError("Entity", entity)

    user = await get_current_user_from_token(authorization, db)
    if not await rbac.check_permission(
        user_id=user.id,
        entity=entity,
        action="update",
        role_ids=user.role_ids,
        is_superuser=user.is_superuser,
    ):
        raise ForbiddenError(f"You don't have permission to perform this action on {meta.label}")

    model = get_entity_model(entity)
    if not model:
        raise NotFoundError("Model", entity)
    row_scope_service.authorize_collection_action(entity, user)

    action_ctx = ActionContext(
        db=db, user=user, entity_name=entity,
        record_id=None, params=body.payload if body else None,
    )
    result = await server_actions.execute(entity, action_name, action_ctx)
    return ActionResponse(**result)


@router.delete("/{entity}/{id}", name="delete_entity")
async def delete_entity(
    entity: str,
    id: str,
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
    rbac: RBACAppService = Depends(get_rbac_service),
    row_scope_service: RowScopeService = Depends(get_row_scope_service),
):
    """Delete a single record by ID using REST DELETE method.

    Returns 200 OK on success. Errors use proper HTTP status codes:
    404 (entity/record not found), 403 (forbidden), 422 (validation),
    409 (foreign key violation).
    """
    meta = MetaRegistry.get(entity)
    if not meta:
        raise NotFoundError("Entity", entity)

    user = await get_current_user_from_token(authorization, db)
    if not await rbac.check_permission(
        user_id=user.id,
        entity=entity,
        action="delete",
        role_ids=user.role_ids,
        is_superuser=user.is_superuser
    ):
        raise ForbiddenError(f"You don't have permission to delete {meta.label}")

    if meta.is_immutable:
        return _err(403, f"{meta.label} records are immutable and cannot be deleted")

    model = get_entity_model(entity)
    if not model:
        raise NotFoundError("Model", entity)

    api = get_entity_api(entity)
    ctx = Context(db=db, user=user, meta=meta)

    repo = EntityRepository(db)
    record = await repo.get_by_id(entity, id)

    if not record:
        raise NotFoundError(meta.label, id)

    if not await row_scope_service.can_access_record(
        record,
        entity,
        str(user.id),
        user.role_ids,
        user.roles or [],
        user.is_superuser,
    ):
        raise ForbiddenError(f"You don't have permission to delete this {meta.label}")

    await row_scope_service.authorize_record_write(entity, record, {}, user)

    ctx.extra["old_values"] = record_to_dict(record)
    ctx.extra["record_id"] = record.id
    delete_errors = await api.validate_delete(record, ctx)
    if delete_errors:
        await db.rollback()
        return _err(422, _build_validation_message(delete_errors, meta), errors=delete_errors)

    try:
        await api.before_delete(record, ctx)
        record_id = record.id
        await db.delete(record)
        await db.commit()
        await api.after_delete(ctx)
        await socket_manager.emit_deleted(entity, record_id)
        return _ok(200, "Record deleted")
    except Exception as e:
        await db.rollback()
        from sqlalchemy.exc import IntegrityError

        if isinstance(e, IntegrityError):
            error_msg = str(e)
            if "foreign key constraint" in error_msg.lower():
                # Find all records that reference this entity
                referencing_records = await repo.find_referencing_records(entity, id)

                # Build a detailed error message with referencing records
                if referencing_records:
                    ref_summary = []
                    for ref in referencing_records[:10]:  # Limit to first 10 records
                        entity_display = ref.get('entity_display', ref['entity'])
                        ref_summary.append(f"{entity_display} ({ref['id']}): {ref['display_name']}")
                    if len(referencing_records) > 10:
                        ref_summary.append(f"... and {len(referencing_records) - 10} more")

                    message = f"Cannot delete {meta.label}. It is still referenced by {len(referencing_records)} record(s)."
                else:
                    message = f"Cannot delete {meta.label}. It is referenced by other records."

                return _err(
                    409,
                    message,
                    data={"referencing_records": referencing_records},
                )
        raise


@router.post("/{entity}/bulk-delete", name="bulk_delete_entity")
async def bulk_delete_entity(
    entity: str,
    request: BulkDeleteRequest,
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
    rbac: RBACAppService = Depends(get_rbac_service),
    row_scope_service: RowScopeService = Depends(get_row_scope_service),
):
    """Delete multiple records by IDs in a single transaction.

    Returns 200 OK on full success, 207 Multi-Status on partial failure
    (body carries per-record details), and proper 4xx for permission/not-found.
    """
    meta = MetaRegistry.get(entity)
    if not meta:
        raise NotFoundError("Entity", entity)

    user = await get_current_user_from_token(authorization, db)
    if not await rbac.check_permission(
        user_id=user.id,
        entity=entity,
        action="delete",
        role_ids=user.role_ids,
        is_superuser=user.is_superuser
    ):
        raise ForbiddenError(f"You don't have permission to delete {meta.label}")

    if meta.is_immutable:
        return _err(403, f"{meta.label} records are immutable and cannot be deleted")

    model = get_entity_model(entity)
    if not model:
        raise NotFoundError("Model", entity)

    api = get_entity_api(entity)
    ctx = Context(db=db, user=user, meta=meta)
    repo = EntityRepository(db)

    # Call before_delete hook for each record
    for record_id in request.ids:
        record = await repo.get_by_id(entity, record_id)
        if record:
            if not await row_scope_service.can_access_record(
                record,
                entity,
                str(user.id),
                user.role_ids,
                user.roles or [],
                user.is_superuser,
            ):
                raise ForbiddenError(f"You don't have permission to delete {meta.label} {record.id}")
            await row_scope_service.authorize_record_write(entity, record, {}, user)
            await api.before_delete(record, ctx)

    # Perform bulk delete
    deleted_count, failed_deletions, error_summary = await repo.bulk_delete(entity, request.ids)

    # Commit the outer transaction after all savepoint commits
    await db.commit()

    # Call after_delete hook once after all deletions
    await api.after_delete(ctx)

    # Emit socket events for deleted records
    for record_id in request.ids:
        # Only emit for successfully deleted records (not in failed list)
        if not any(f['id'] == record_id for f in failed_deletions):
            await socket_manager.emit_deleted(entity, record_id)

    entity_label = meta.label or entity.replace("_", " ").title()

    # Build response
    if failed_deletions:
        # Partial or complete failure - 207 Multi-Status so frontend shows toast
        if deleted_count == 0:
            message = f"Could not delete {len(request.ids)} {entity_label} record(s)."
        else:
            message = f"Deleted {deleted_count} of {len(request.ids)} {entity_label} record(s)."

        # Build summarized error message
        if error_summary:
            error_lines = []
            for error_type, count in error_summary.items():
                if error_type == "Foreign key constraint violation":
                    error_lines.append(f"{count} {entity_label} record(s) still referenced by other records.")
                elif error_type == "Record not found":
                    error_lines.append(f"{count} record(s) not found.")
                elif error_type == "Model not found":
                    error_lines.append(f"Model for {entity} not found.")
                else:
                    error_lines.append(f"{count} record(s) had {error_type.lower()}.")
            message += " Errors: " + " ".join(error_lines)

        return _err(
            207,
            message,
            data={
                "deleted_count": deleted_count,
                "failed_count": len(failed_deletions),
                "failed_deletions": failed_deletions,
                "error_summary": error_summary,
            },
        )

    # Full success
    return _ok(
        200,
        f"Successfully deleted {deleted_count} {entity_label} record(s)",
        data={"deleted_count": deleted_count},
    )
