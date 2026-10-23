import uuid
from datetime import datetime
from typing import List, TYPE_CHECKING
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

if TYPE_CHECKING:
    from app.core.framework.models.workflow_state_link import WorkflowStateLink


class Workflow(Base):
    """Workflow entity model."""
    __tablename__ = "core_workflows"
    __table_args__ = (
        Index(
            "uq_core_workflows_default_scope",
            "workspace_id",
            "target_entity",
            unique=True,
            sqlite_where=text("is_default = 1"),
            postgresql_where=text("is_default"),
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    target_entity: Mapped[str] = mapped_column(String(255), nullable=False)
    workspace_id: Mapped[str | None] = mapped_column(
        String(50), ForeignKey("workspace.id"), nullable=True, index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=True, default=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    state_links: Mapped[List["WorkflowStateLink"]] = relationship(
        "WorkflowStateLink",
        back_populates="workflow",
        cascade="all, delete-orphan",
    )
