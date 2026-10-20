from datetime import date
from sqlalchemy import Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.core.base_model import BaseModel


class Project(BaseModel):
    """Project entity model."""
    __tablename__ = "project"
    
    name: Mapped[str] = mapped_column(String(255), nullable=True, default=None)
    workspace_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("workspace.id"), nullable=True, default=None, index=True
    )
    team_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("workspace_team.id"), nullable=True, default=None, index=True
    )
    description: Mapped[str] = mapped_column(Text, nullable=True, default=None)
    color: Mapped[str] = mapped_column(String(255), nullable=True, default="#3b82f6")
    icon: Mapped[str] = mapped_column(String(255), nullable=True, default="folder")
    manager_id: Mapped[str] = mapped_column(String(50), ForeignKey("core_users.id"), nullable=True, default=None)
    status: Mapped[str] = mapped_column(String(100), nullable=True, default="active")
    start_date: Mapped[date] = mapped_column(Date, nullable=True, default=None)
    end_date: Mapped[date] = mapped_column(Date, nullable=True, default=None)
