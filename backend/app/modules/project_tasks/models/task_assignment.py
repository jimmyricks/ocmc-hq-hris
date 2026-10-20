from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from app.core.base_model import BaseModel


class TaskAssignment(BaseModel):
    """Task Assignment entity model."""
    __tablename__ = "task_assignment"
    
    task_id: Mapped[str] = mapped_column(String(50), ForeignKey("task.id"), nullable=True, default=None)
    idx: Mapped[int] = mapped_column(Integer, nullable=True, default=0)
    user_id: Mapped[str] = mapped_column(String(50), ForeignKey("core_users.id"), nullable=True, default=None)
    assigned_by: Mapped[str] = mapped_column(String(50), ForeignKey("core_users.id"), nullable=True, default=None)
    assigned_at: Mapped[datetime] = mapped_column(DateTime, nullable=True, default=None)
    unassigned_at: Mapped[datetime] = mapped_column(DateTime, nullable=True, default=None)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=True, default=True)
    status: Mapped[str] = mapped_column(String(100), nullable=True, default="active")
