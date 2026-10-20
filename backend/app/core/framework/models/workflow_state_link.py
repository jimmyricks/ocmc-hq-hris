import uuid
from typing import TYPE_CHECKING, Optional
from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

if TYPE_CHECKING:
    from app.core.framework.models.workflow import Workflow
    from app.core.framework.models.workflow_state import WorkflowState
    from app.core.framework.models.workflow_transition import WorkflowTransition


class WorkflowStateLink(Base):
    """Workflow State Link entity model."""
    __tablename__ = "core_workflow_state_links"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    workflow_id: Mapped[str] = mapped_column(String(36), ForeignKey("core_workflows.id"), nullable=True, default=None)
    state_id: Mapped[str] = mapped_column(String(36), ForeignKey("core_workflow_states.id"), nullable=True, default=None)
    is_initial: Mapped[bool] = mapped_column(Boolean, nullable=True, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=True, default=0)
    visual_config: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)

    workflow: Mapped["Workflow"] = relationship("Workflow", back_populates="state_links")
    state: Mapped["WorkflowState"] = relationship("WorkflowState", back_populates="workflow_links")
    # transitions where this link is the source
    outgoing_transitions = relationship(
        "WorkflowTransition", foreign_keys="[WorkflowTransition.from_state_link_id]",
        cascade="all, delete-orphan", back_populates="from_state_link"
    )
    # transitions where this link is the target
    incoming_transitions = relationship(
        "WorkflowTransition", foreign_keys="[WorkflowTransition.to_state_link_id]",
        cascade="all, delete-orphan", back_populates="to_state_link"
    )

    def get_visual_config(self) -> dict:
        """Parse visual_config JSON string into a dict."""
        if not self.visual_config:
            return {}
        try:
            import json
            return json.loads(self.visual_config)
        except (json.JSONDecodeError, TypeError):
            return {}

    def set_visual_config(self, config: dict | None):
        """Set visual_config from a dict."""
        import json
        self.visual_config = json.dumps(config) if config else None
