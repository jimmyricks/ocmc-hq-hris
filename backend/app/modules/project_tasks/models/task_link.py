from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column
from app.core.base_model import BaseModel


class TaskLink(BaseModel):
    """Task Link entity model."""
    __tablename__ = "task_link"
    
    task_id: Mapped[str] = mapped_column(String(50), ForeignKey("task.id"), nullable=True, default=None)
    url: Mapped[str] = mapped_column(String(255), nullable=True, default=None)
    label: Mapped[str] = mapped_column(String(255), nullable=True, default=None)
