import json
import uuid
from typing import TYPE_CHECKING, Optional
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

if TYPE_CHECKING:
    from app.core.framework.models.workflow_state_link import WorkflowStateLink
    from app.core.framework.models.workflow_action import WorkflowAction


class WorkflowTransition(Base):
    """Workflow Transition entity model."""
    __tablename__ = "core_workflow_transitions"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    from_state_link_id: Mapped[str] = mapped_column(String(36), ForeignKey("core_workflow_state_links.id"), nullable=False)
    action_id: Mapped[str] = mapped_column(String(36), ForeignKey("core_workflow_actions.id"), nullable=True, default=None)
    to_state_link_id: Mapped[str] = mapped_column(String(36), ForeignKey("core_workflow_state_links.id"), nullable=False)
    allowed_roles: Mapped[str] = mapped_column(Text, nullable=True, default=None)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=True, default=0)
    visual_config: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)

    from_state_link: Mapped["WorkflowStateLink"] = relationship("WorkflowStateLink", foreign_keys=[from_state_link_id], back_populates="outgoing_transitions")
    action_ref: Mapped["WorkflowAction"] = relationship("WorkflowAction", back_populates="transitions")
    to_state_link: Mapped["WorkflowStateLink"] = relationship("WorkflowStateLink", foreign_keys=[to_state_link_id], back_populates="incoming_transitions")

    def get_allowed_roles(self) -> list[str]:
        """Parse allowed_roles JSON string into a list."""
        if not self.allowed_roles:
            return []
        try:
            return json.loads(self.allowed_roles)
        except (json.JSONDecodeError, TypeError):
            return []

    def set_allowed_roles(self, roles: list[str] | None):
        """Set allowed_roles from a list."""
        if not roles:
            self.allowed_roles = None
        else:
            self.allowed_roles = json.dumps(roles)

    def get_visual_config(self) -> dict:
        """Parse visual_config JSON string into a dict."""
        if not self.visual_config:
            return {}
        try:
            return json.loads(self.visual_config)
        except (json.JSONDecodeError, TypeError):
            return {}

    def set_visual_config(self, config: dict | None):
        """Set visual_config from a dict."""
        self.visual_config = json.dumps(config) if config else None
