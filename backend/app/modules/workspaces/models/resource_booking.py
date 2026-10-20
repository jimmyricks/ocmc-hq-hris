from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import BaseModel


class ResourceBooking(BaseModel):
    __tablename__ = "resource_booking"
    __table_args__ = (
        UniqueConstraint(
            "resource_id", "starts_at", "ends_at", name="uq_resource_booking_interval"
        ),
    )

    workspace_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("workspace.id"), nullable=False, index=True
    )
    resource_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("workspace_resource.id"), nullable=False, index=True
    )
    event_id: Mapped[str | None] = mapped_column(
        String(50), ForeignKey("planner_event.id"), nullable=True
    )
    occurrence_id: Mapped[str | None] = mapped_column(
        String(50), ForeignKey("schedule_occurrence.id"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    ends_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="confirmed")
