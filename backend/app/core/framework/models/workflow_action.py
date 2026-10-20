"""
Core Framework Workflow Action Model
=====================================
WorkflowAction entity model for the Core Framework.
"""
import uuid
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import String, DateTime, event
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.core.framework.models.workflow_state import generate_slug

if TYPE_CHECKING:
    from app.core.framework.models.workflow_transition import WorkflowTransition


class WorkflowAction(Base):
    """Workflow Action entity model."""
    __tablename__ = "core_workflow_actions"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    label: Mapped[str] = mapped_column(String(255), nullable=True)
    slug: Mapped[Optional[str]] = mapped_column(String(100), unique=True, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    transitions: Mapped[List["WorkflowTransition"]] = relationship(
        "WorkflowTransition",
        back_populates="action_ref",
        cascade="all, delete-orphan",
    )


@event.listens_for(WorkflowAction, "before_insert")
@event.listens_for(WorkflowAction, "before_update")
def generate_action_slug(mapper, connection, target):
    if target.label:
        target.slug = generate_slug(target.label)
