"""
Document Mutation Service
=========================
Write operations for documents (SRP: mutations only).

Provides:
- DocumentMutationService: Class-based service with dependency injection
- new_doc: Create a new document instance (not saved) - legacy wrapper
- save_doc: Save a document (insert or update) - legacy wrapper
- insert_doc: Insert a new document - legacy wrapper
- delete_doc: Delete a document - legacy wrapper
- apply_workflow_state: Validate and apply a workflow transition - legacy wrapper
"""
from dataclasses import dataclass
from typing import Any, Optional
from sqlalchemy import select, inspect
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.documents.document_service import DocumentAppService
from app.application.services.documents.naming_service import NamingAppService
from app.infrastructure.database.repositories.document_repository import DocumentRepository
from app.infrastructure.database.repositories.naming_repository import NamingRepository
from app.infrastructure.database.repositories.workflow_repository import WorkflowRepository
from app.application.services.documents.document_query import _get_model, get_meta, _record_to_dict
from app.domain.exceptions import DocumentNotFoundError, WorkflowTransitionError
from app.core.framework.models.workflow_state import generate_slug
from app.application.utils.doc_utils import get_user_id


@dataclass
class WorkflowTransitionResult:
    """Result of a workflow transition."""
    from_state: str
    to_state: str
    success: bool = True


class DocumentMutationService:
    """Class-based document mutation service with dependency injection."""

    def __init__(
        self,
        db: AsyncSession,
        naming_repo: Optional[NamingRepository] = None,
        workflow_repo: Optional[WorkflowRepository] = None,
        document_repo: Optional[DocumentRepository] = None,
    ):
        self.db = db
        self.naming_repo = naming_repo or NamingRepository(db)
        self.workflow_repo = workflow_repo or WorkflowRepository(db)
        self.document_repo = document_repo or DocumentRepository(db)

    async def new_doc(
        self,
        entity: str,
        **kwargs
    ) -> Any:
        """Create a new document instance (not saved to database yet)."""
        model = _get_model(entity)
        if not model:
            raise DocumentNotFoundError(entity, "model not found")

        meta = get_meta(entity)

        # Generate ID if naming is enabled and no ID provided
        if meta and meta.naming and meta.naming.enabled and "id" not in kwargs:
            naming_service = NamingAppService(self.naming_repo)
            generated_id = await naming_service.generate_id(meta.naming, entity)
            if generated_id:
                kwargs["id"] = generated_id

        # Set initial workflow state if workflow enabled and no state provided
        if (meta and meta.workflow and meta.workflow.enabled and
            meta.workflow.state_field and meta.workflow.initial_state and
            meta.workflow.state_field not in kwargs):
            kwargs[meta.workflow.state_field] = generate_slug(meta.workflow.initial_state)

        doc = model(**kwargs)
        return doc

    async def _notify_if_insert(self, doc: Any, was_insert: bool) -> None:
        """Send notification if document was inserted."""
        if not was_insert:
            return

        from app.application.email_notifications.document_notify import (
            notify_after_document_insert,
        )
        await notify_after_document_insert(self.db, doc)

    async def save_doc(
        self,
        doc: Any,
        commit: bool = True
    ) -> Any:
        """Save a document to the database (insert or update)."""
        insp = inspect(doc)
        was_insert = insp.transient
        if insp.transient:
            self.db.add(doc)

        if commit:
            await self.db.commit()
            await self.db.refresh(doc)
        else:
            await self.db.flush()

        await self._notify_if_insert(doc, was_insert)

        return doc

    async def insert_doc(
        self,
        doc: Any,
        commit: bool = True
    ) -> Any:
        """Insert a new document."""
        self.db.add(doc)
        if commit:
            await self.db.commit()
            await self.db.refresh(doc)
        else:
            await self.db.flush()
        await self._notify_if_insert(doc, was_insert=True)
        return doc

    async def delete_doc(
        self,
        entity: str,
        id: str,
        commit: bool = True
    ) -> None:
        """Delete a document by entity name and ID."""
        document_service = DocumentAppService(self.document_repo)
        doc = await document_service.get_doc(entity, id)
        if not doc:
            raise DocumentNotFoundError(entity, id)

        await self.db.delete(doc)
        if commit:
            await self.db.commit()

    async def apply_workflow_state(
        self,
        entity: str,
        doc: Any,
        action_slug: str,
        user: Any = None,
    ) -> WorkflowTransitionResult:
        """
        Validate a workflow transition and apply the new state to a document.

        This is the ONLY correct way to change workflow_state on a document.
        Never set workflow_state directly — always go through this function so
        that the transition is validated against the workflow configuration in
        the database.
        """
        meta = get_meta(entity)
        state_field = "workflow_state"
        if meta and meta.workflow and meta.workflow.state_field:
            state_field = meta.workflow.state_field

        current_state_raw = getattr(doc, state_field, None) or ""
        current_state = generate_slug(current_state_raw)

        if not current_state:
            initial = await self.workflow_repo.get_initial_state(entity)
            if initial:
                current_state = initial
            else:
                raise WorkflowTransitionError(
                    f"No workflow configured for '{entity}'",
                    action=action_slug
                )

        is_valid, target_state, error = await self.workflow_repo.validate_transition(
            entity, current_state, action_slug, user=user
        )

        if not is_valid:
            raise WorkflowTransitionError(
                error or f"Action '{action_slug}' not valid from state '{current_state}'",
                from_state=current_state,
                action=action_slug
            )

        setattr(doc, state_field, target_state)

        # Deferred import to avoid circular dependency:
        # document_mutation → workflow_ledger_service → document → document_mutation
        from app.application.services.workflows.workflow_ledger_service import log_workflow_transition
        await log_workflow_transition(
            entity_type=entity,
            record_id=getattr(doc, 'id', None),
            previous_state=current_state,
            next_state=target_state,
            action=action_slug,
            changed_by=get_user_id(user),
            db=self.db,
        )

        return WorkflowTransitionResult(
            from_state=current_state,
            to_state=target_state,
            success=True
        )


# =============================================================================
# Legacy wrapper functions (for backward compatibility)
# =============================================================================

async def new_doc(
    entity: str,
    db: AsyncSession,
    **kwargs
) -> Optional[Any]:
    """Create a new document instance (not saved to database yet). Legacy wrapper."""
    try:
        service = DocumentMutationService(db)
        return await service.new_doc(entity, **kwargs)
    except DocumentNotFoundError:
        return None


async def save_doc(
    doc: Any,
    db: AsyncSession,
    commit: bool = True
) -> Any:
    """Save a document to the database (insert or update). Legacy wrapper."""
    service = DocumentMutationService(db)
    return await service.save_doc(doc, commit)


async def insert_doc(
    doc: Any,
    db: AsyncSession,
    commit: bool = True
) -> Any:
    """Insert a new document. Legacy wrapper."""
    service = DocumentMutationService(db)
    return await service.insert_doc(doc, commit)


async def delete_doc(
    entity: str,
    id: str,
    db: AsyncSession,
    commit: bool = True
) -> bool:
    """Delete a document by entity name and ID. Legacy wrapper."""
    try:
        service = DocumentMutationService(db)
        await service.delete_doc(entity, id, commit)
        return True
    except DocumentNotFoundError:
        return False


async def apply_workflow_state(
    entity: str,
    doc: Any,
    action_slug: str,
    db: AsyncSession,
    commit: bool = False,
    user: Any = None,
) -> dict:
    """
    Validate a workflow transition and apply the new state to a document.
    Legacy wrapper - returns dict for backward compatibility.

    This is the ONLY correct way to change workflow_state on a document.
    Never set workflow_state directly — always go through this function so
    that the transition is validated against the workflow configuration in
    the database.
    """
    try:
        service = DocumentMutationService(db)
        result = await service.apply_workflow_state(entity, doc, action_slug, user)
        
        if commit:
            await db.flush()
        
        return {
            "status": "success",
            "from_state": result.from_state,
            "to_state": result.to_state,
        }
    except WorkflowTransitionError as e:
        return {
            "status": "error",
            "message": e.message,
        }
