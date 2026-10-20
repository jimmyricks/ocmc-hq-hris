from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column
from app.core.base_model import BaseModel


class ProjectMember(BaseModel):
    """Project Member entity model."""
    __tablename__ = "project_member"
    
    project_id: Mapped[str] = mapped_column(String(50), ForeignKey("project.id"), nullable=True, default=None)
    user_id: Mapped[str] = mapped_column(String(50), ForeignKey("core_users.id"), nullable=True, default=None)
    role: Mapped[str] = mapped_column(String(100), nullable=True, default="member")
    joined_at: Mapped[datetime] = mapped_column(DateTime, nullable=True, default=None)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=True, default=True)
