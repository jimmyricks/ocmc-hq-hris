from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, false
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import BaseModel


class ScheduleSeries(BaseModel):
    __tablename__ = "schedule_series"

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
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, default="lesson")
    frequency: Mapped[str] = mapped_column(String(20), nullable=False)
    interval: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    weekdays: Mapped[str | None] = mapped_column(String(20), nullable=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    until_date: Mapped[date] = mapped_column(Date, nullable=False)
    timezone: Mapped[str] = mapped_column(String(100), nullable=False, default="UTC")
    artist_portal_visible: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
