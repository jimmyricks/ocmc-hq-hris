"""
Workflow Ledger Service
========================
Service for tracking all workflow state changes in the system.

This service logs every workflow transition to the workflow_ledger table,
providing a complete audit trail of who changed what, when, and from/to which states.
"""
import logging
from datetime import datetime
from typing import Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.documents.document import save_doc
from app.application.utils.doc_utils import get_user_id
from app.core.framework.models.infrastructure import WorkflowLedger

logger = logging.getLogger(__name__)


class WorkflowLedgerService:
    """Service for logging workflow state changes."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def log_transition(
        self,
        entity_type: str,
        record_id: str,
        previous_state: Optional[str],
        next_state: str,
        action: Optional[str],
        changed_by: Optional[str],
        triggered_by_entity_type: Optional[str] = None,
        triggered_by_record_id: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Any:
        try:
            ledger_entry = WorkflowLedger(
                entity_type=entity_type,
                record_id=record_id,
                previous_state=previous_state,
                next_state=next_state,
                action=action,
                changed_by=changed_by,
                changed_at=datetime.utcnow(),
                triggered_by_entity_type=triggered_by_entity_type,
                triggered_by_record_id=triggered_by_record_id,
                notes=notes,
            )
            await save_doc(ledger_entry, self.db, commit=False)
            return ledger_entry
        except Exception:
            logger.exception("Failed to log workflow transition for %s/%s", entity_type, record_id)
            return None

    async def apply_cascading_state_change(
        self,
        doc: Any,
        entity_type: str,
        new_state: str,
        action: str,
        user: Any,
        source_entity_type: str,
        source_record_id: str,
        notes: Optional[str] = None,
        commit: bool = False,
    ) -> None:
        """Update a document's workflow_state and log the cascading transition.

        Centralizes the repeated pattern of:
        1. Capture previous state
        2. Set new state
        3. Save document
        4. Log to workflow ledger with source attribution
        """
        previous_state = getattr(doc, 'workflow_state', None)
        doc.workflow_state = new_state
        await save_doc(doc, self.db, commit=commit)
        await self.log_transition(
            entity_type=entity_type,
            record_id=getattr(doc, 'id', None),
            previous_state=previous_state,
            next_state=new_state,
            action=action,
            changed_by=get_user_id(user),
            triggered_by_entity_type=source_entity_type,
            triggered_by_record_id=source_record_id,
            notes=notes,
        )


async def log_workflow_transition(
    entity_type: str,
    record_id: str,
    previous_state: Optional[str],
    next_state: str,
    action: Optional[str],
    changed_by: Optional[str],
    db: AsyncSession,
    triggered_by_entity_type: Optional[str] = None,
    triggered_by_record_id: Optional[str] = None,
    notes: Optional[str] = None,
) -> Any:
    """Legacy wrapper for logging workflow transitions."""
    service = WorkflowLedgerService(db)
    return await service.log_transition(
        entity_type=entity_type,
        record_id=record_id,
        previous_state=previous_state,
        next_state=next_state,
        action=action,
        changed_by=changed_by,
        triggered_by_entity_type=triggered_by_entity_type,
        triggered_by_record_id=triggered_by_record_id,
        notes=notes,
    )


async def apply_cascading_state_change(
    doc: Any,
    entity_type: str,
    new_state: str,
    action: str,
    user: Any,
    db: AsyncSession,
    source_entity_type: str,
    source_record_id: str,
    notes: Optional[str] = None,
    commit: bool = False,
) -> None:
    """Legacy wrapper for applying cascading state changes."""
    service = WorkflowLedgerService(db)
    await service.apply_cascading_state_change(
        doc=doc,
        entity_type=entity_type,
        new_state=new_state,
        action=action,
        user=user,
        source_entity_type=source_entity_type,
        source_record_id=source_record_id,
        notes=notes,
        commit=commit,
    )
