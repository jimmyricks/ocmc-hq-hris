from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, false
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import BaseModel


class PlannerEvent(BaseModel):
    __tablename__ = "planner_event"

    workspace_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("workspace.id"), nullable=False, index=True
    )
    team_id: Mapped[str | None] = mapped_column(
        String(50), ForeignKey("workspace_team.id"), nullable=True, index=True
    )
    project_id: Mapped[str | None] = mapped_column(
        String(50), ForeignKey("project.id"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, default="event")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="scheduled")
    starts_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    ends_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    timezone: Mapped[str] = mapped_column(String(100), nullable=False, default="UTC")
    all_day: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    artist_portal_visible: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
