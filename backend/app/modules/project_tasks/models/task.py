from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.core.base_model import BaseModel


class Task(BaseModel):
    """Task entity model."""
    __tablename__ = "task"
    
    project_id: Mapped[str] = mapped_column(String(50), ForeignKey("project.id"), nullable=True, default=None)
    task_type_id: Mapped[str] = mapped_column(String(50), ForeignKey("task_type.id"), nullable=True, default=None)
    category_id: Mapped[str] = mapped_column(String(50), ForeignKey("task_category.id"), nullable=True, default=None)
    title: Mapped[str] = mapped_column(String(255), nullable=True, default=None)
    description: Mapped[str] = mapped_column(Text, nullable=True, default=None)
    priority: Mapped[str] = mapped_column(String(100), nullable=True, default="medium")
    status: Mapped[str] = mapped_column(String(100), nullable=True, default="pending")
    due_date: Mapped[datetime] = mapped_column(DateTime, nullable=True, default=None)
    planned_start_at: Mapped[datetime] = mapped_column(DateTime, nullable=True, default=None)
    planned_end_at: Mapped[datetime] = mapped_column(DateTime, nullable=True, default=None)
