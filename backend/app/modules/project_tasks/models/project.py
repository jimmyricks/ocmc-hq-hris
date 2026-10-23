from datetime import date
from sqlalchemy import Boolean, CheckConstraint, Date, ForeignKey, String, Text, UniqueConstraint, false
from sqlalchemy.orm import Mapped, mapped_column
from app.core.base_model import BaseModel


class Project(BaseModel):
    """Project entity model."""
    __tablename__ = "project"
    __table_args__ = (
        UniqueConstraint("id", "workspace_id", name="uq_project_id_workspace"),
        CheckConstraint(
            "integration_kind IS NULL OR integration_kind IN ('album', 'photoshoot', 'other')",
            name="ck_project_integration_kind",
        ),
    )
    
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
    is_continuous: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
    bahandi_artist_id: Mapped[int | None] = mapped_column(nullable=True, index=True)
    integration_kind: Mapped[str | None] = mapped_column(String(30), nullable=True)
    artist_portal_visible: Mapped[bool | None] = mapped_column(
        Boolean, nullable=True, default=False, server_default=false()
    )
    public_summary: Mapped[str | None] = mapped_column(String(2000), nullable=True)
