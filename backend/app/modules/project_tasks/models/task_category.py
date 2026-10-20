from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from app.core.base_model import BaseModel


class TaskCategory(BaseModel):
    """Task Category entity model."""
    __tablename__ = "task_category"
    
    name: Mapped[str] = mapped_column(String(255), nullable=True, default=None)
    color: Mapped[str] = mapped_column(String(255), nullable=True, default="#64748b")
    icon: Mapped[str] = mapped_column(String(255), nullable=True, default="clipboard")
