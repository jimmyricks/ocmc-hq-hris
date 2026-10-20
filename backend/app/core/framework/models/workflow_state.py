"""
Core Framework Workflow State Model
====================================
WorkflowState entity model and slug generation utility.
"""
import re
import uuid
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import String, DateTime, event
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

if TYPE_CHECKING:
    from app.core.framework.models.workflow_state_link import WorkflowStateLink


def generate_slug(label: str) -> str:
    """Convert label to slug: lowercase, replace spaces with underscores, remove special chars."""
    slug = label.lower().strip()
    slug = re.sub(r"[^a-z0-9\s_]", "", slug)
    slug = re.sub(r"\s+", "_", slug)
    return slug


class WorkflowState(Base):
    """Workflow State entity model."""
    __tablename__ = "core_workflow_states"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    label: Mapped[str] = mapped_column(String(255), nullable=True)
    slug: Mapped[Optional[str]] = mapped_column(String(100), unique=True, nullable=True, default=None)
    color: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, default="neutral")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    workflow_links: Mapped[List["WorkflowStateLink"]] = relationship(
        "WorkflowStateLink",
        back_populates="state",
        cascade="all, delete-orphan",
    )


@event.listens_for(WorkflowState, "before_insert")
@event.listens_for(WorkflowState, "before_update")
def generate_state_slug(mapper, connection, target):
    if target.label:
        target.slug = generate_slug(target.label)
