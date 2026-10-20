from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import BaseModel


class ScheduleOccurrence(BaseModel):
    __tablename__ = "schedule_occurrence"
    __table_args__ = (
        UniqueConstraint("series_id", "starts_at", name="uq_schedule_occurrence_start"),
    )

    series_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("schedule_series.id"), nullable=False, index=True
    )
    starts_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="scheduled")
    title_override: Mapped[str | None] = mapped_column(String(255), nullable=True)
