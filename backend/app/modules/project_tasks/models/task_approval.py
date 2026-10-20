from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.core.base_model import BaseModel


class TaskApproval(BaseModel):
    """Task Approval entity model."""
    __tablename__ = "task_approval"
    
    task_submission_id: Mapped[str] = mapped_column(String(50), ForeignKey("task_submission.id"), nullable=True, default=None)
    idx: Mapped[int] = mapped_column(Integer, nullable=True, default=0)
    approver_id: Mapped[str] = mapped_column(String(50), ForeignKey("core_users.id"), nullable=True, default=None)
    decision: Mapped[str] = mapped_column(String(100), nullable=True, default=None)
    remarks: Mapped[str] = mapped_column(Text, nullable=True, default=None)
    decided_at: Mapped[datetime] = mapped_column(DateTime, nullable=True, default=None)
