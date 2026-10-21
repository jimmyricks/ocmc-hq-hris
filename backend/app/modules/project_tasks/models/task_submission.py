from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.core.base_model import BaseModel


class TaskSubmission(BaseModel):
    """Task Submission entity model."""
    __tablename__ = "task_submission"
    
    task_assignment_id: Mapped[str] = mapped_column(String(50), ForeignKey("task_assignment.id"), nullable=True, default=None)
    version: Mapped[int] = mapped_column(Integer, nullable=True, default=1)
    previous_submission_id: Mapped[str] = mapped_column(String(50), ForeignKey("task_submission.id"), nullable=True, default=None)
    notes: Mapped[str] = mapped_column(Text, nullable=True, default=None)
    status: Mapped[str] = mapped_column(String(100), nullable=True, default="draft")
    submitted_by: Mapped[str] = mapped_column(String(50), ForeignKey("core_users.id"), nullable=True, default=None)
    submitted_at: Mapped[datetime] = mapped_column(DateTime, nullable=True, default=None)
    external_link: Mapped[str] = mapped_column(String(255), nullable=True, default=None)
    approved_rate: Mapped[float] = mapped_column(Numeric(12, 2), nullable=True, default=None)
    approved_quantity: Mapped[float] = mapped_column(Numeric(12, 2), nullable=True, default=None)
    approved_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=True, default=None)
