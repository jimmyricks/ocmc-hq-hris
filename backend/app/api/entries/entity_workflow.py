"""
Entity Workflow Routes
=======================
Workflow transition operations for entities.
"""
from typing import Any, Optional
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_current_user_from_token, CurrentUser
from app.core.serialization import record_to_dict
from app.core.framework.models.workflow_state import generate_slug
from app.meta.registry import MetaRegistry
from app.api.dependencies import (
    get_db,
    get_rbac_service,
    get_row_scope_service,
    get_workflow_progress_service,
    get_workflow_repo,
)
from app.application.services.access_control.rbac_service import RBACAppService
from app.application.services.access_control.row_scope_service import RowScopeService
from app.application.utils.doc_utils import format_state_label, get_user_id
from app.schemas.base import ActionResponse, WorkflowRequest
from app.infrastructure.database.repositories.workflow_repository import WorkflowRepository
from app.application.hooks.registry import hook_registry
from app.application.hooks.context import WorkflowContext
from app.application.services.notifications.socketio import socket_manager
from app.infrastructure.database.repositories.entity_repository import get_entity_model
from app.application.services.workflows.workflow_progress_service import WorkflowProgressService
from app.application.services.workflows.workflow_ledger_service import log_workflow_transition
from app.application.email_notifications.document_notify import notify_after_workflow_transition

router = APIRouter(tags=["entity"])


def _workflow_state_field(meta: Any, model: Any) -> str | None:
    configured = getattr(getattr(meta, "workflow", None), "state_field", None)
    field = configured or "workflow_state"
    if hasattr(model, field):
        return field
    return "status" if hasattr(model, "status") else None


@router.get("/{entity}/{record_id}/workflow-progress")
async def get_workflow_progress(
    entity: str,
    record_id: str,
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
    rbac: RBACAppService = Depends(get_rbac_service),
    row_scope_service: RowScopeService = Depends(get_row_scope_service),
    workflow_progress_service: WorkflowProgressService = Depends(get_workflow_progress_service),
):
    user = await get_current_user_from_token(authorization, db)
    has_permission = await rbac.check_permission(
        user.id,
        entity,
        "read",
        role_ids=user.role_ids,
        is_superuser=user.is_superuser,
    )
    if not has_permission and not await row_scope_service.can_read_entity(
        entity, user.id, user.roles, user.is_superuser
    ):
        raise HTTPException(status_code=403, detail="Permission denied")
    model = get_entity_model(entity)
    if not model:
        raise HTTPException(status_code=404, detail=f"Entity '{entity}' not found")
    result = await db.execute(select(model).where(model.id == record_id))
    record = result.scalar_one_or_none()
    if not record or not await row_scope_service.can_access_record(
        record, entity, user.id, user.role_ids, user.roles, user.is_superuser
    ):
        raise HTTPException(status_code=403, detail="Permission denied")
    try:
        data = await workflow_progress_service.get_progress(entity, record_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ActionResponse(
        status="success",
        message="Workflow progress retrieved successfully",
        data=data,
    )


@router.post("/{entity}/workflow")
async def workflow_action(
    entity: str,
    request: WorkflowRequest,
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
    workflow_repo: WorkflowRepository = Depends(get_workflow_repo),
    row_scope_service: RowScopeService = Depends(get_row_scope_service),
):
    """Execute a workflow transition."""
    meta = MetaRegistry.get(entity)
    if not meta:
        return ActionResponse(
            status="error",
            message=f"Entity '{entity}' not found",
            errors={"entity": f"Unknown entity: {entity}"}
        )

    model = get_entity_model(entity)
    if not model:
        return ActionResponse(
            status="error",
            message=f"Model for '{entity}' not found",
            errors={"model": f"No SQLAlchemy model registered for: {entity}"}
        )

    state_field = _workflow_state_field(meta, model)
    if not state_field:
        return ActionResponse(
            status="error",
            message=f"Entity '{entity}' has no persisted workflow state field",
            errors={"workflow_state": f"No state field configured for {entity}"},
        )

    user = await get_current_user_from_token(authorization, db)

    workflow = await workflow_repo.get_workflow(entity)
    if not workflow:
        return ActionResponse(
            status="error",
            message=f"No workflow configured for entity '{entity}'",
            errors={"workflow": f"Create a workflow with target_entity='{entity}' first"}
        )

    result = await db.execute(select(model).where(model.id == request.id))
    doc = result.scalar_one_or_none()

    if not doc:
        return ActionResponse(
            status="error",
            message=f"Record '{request.id}' not found",
            errors={"id": f"No {meta.label} found with ID: {request.id}"}
        )

    if not await row_scope_service.can_access_record(
        doc, entity, user.id, user.role_ids, user.roles, user.is_superuser
    ):
        raise HTTPException(status_code=403, detail="Permission denied")
    await row_scope_service.authorize_record_write(entity, doc, {}, user)

    # Get current state and normalize to slug format
    current_state_raw = getattr(doc, state_field, None)
    if not current_state_raw:
        initial_link = next((sl for sl in workflow.state_links if sl.is_initial), None)
        current_state = initial_link.state.slug if initial_link else None
    else:
        current_state = generate_slug(str(current_state_raw))

    # Validate transition
    is_valid, target_state, error = await workflow_repo.validate_transition(
        entity,
        current_state,
        request.action,
        user,
        request.id,
        workflow=workflow,
        doc=doc,
    )

    if not is_valid:
        return ActionResponse(
            status="error",
            message=error,
            errors={"action": f"Cannot perform '{request.action}' from state '{current_state}'"}
        )

    # Resolve human-readable action label for workflow hooks
    action_label = None
    for state_link in workflow.state_links:
        for t in state_link.outgoing_transitions:
            if t.action_ref.slug == request.action:
                action_label = t.action_ref.label
                break
        if action_label:
            break
    if not action_label:
        action_label = request.action  # fallback to slug

    # Run workflow hook (pass human-readable label as action)
    wf_ctx = WorkflowContext(
        db=db, user=user, entity=entity, doc=doc,
        record_id=request.id, action=action_label,
        from_state=current_state, to_state=target_state
    )
    hook_result = await hook_registry.execute_workflow(entity, wf_ctx)

    if hook_result["status"] == "error":
        # Rollback any partial writes from the hook before returning error
        await db.rollback()
        return ActionResponse(
            status="error",
            message=hook_result["message"],
            errors=hook_result.get("errors")
        )

    # Apply state transition on the parent doc
    setattr(doc, state_field, target_state)

    # Log the workflow transition to the ledger
    await log_workflow_transition(
        entity_type=entity,
        record_id=request.id,
        previous_state=current_state,
        next_state=target_state,
        action=request.action,
        changed_by=get_user_id(user),
        db=db,
    )

    await db.commit()
    await db.refresh(doc)

    doc_dict = record_to_dict(doc)
    if target_state:
        await notify_after_workflow_transition(db, entity, doc_dict, target_state)

    await socket_manager.emit_workflow(entity, doc_dict, request.action, current_state, target_state)

    # Build response — pass through redirect data if the hook created a new record
    response_data = doc_dict
    if hook_result.get("action") == "generate_id":
        response_data = {
            **doc_dict,
            "redirect_action": "generate_id",
            "redirect_path": hook_result.get("path"),
        }
    if hook_result.get("auto_closed"):
        response_data = {
            **doc_dict,
            "auto_closed": True,
            "parent_entity": hook_result.get("parent_entity"),
            "parent_id": hook_result.get("parent_id"),
        }

    # Use hook's message if it provided override_message, otherwise use generic transition message
    message = hook_result.get("message") if hook_result.get("override_message") else f"Successfully transitioned from '{format_state_label(current_state)}' to '{format_state_label(target_state)}'"

    return ActionResponse(
        status="success",
        message=message,
        data=response_data
    )
