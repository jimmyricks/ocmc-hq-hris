from datetime import datetime
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column
from app.core.base_model import BaseModel


class Task(BaseModel):
    """Task entity model."""
    __tablename__ = "task"
    __table_args__ = (
        CheckConstraint(
            "workspace_id IS NULL OR project_id IS NOT NULL",
            name="ck_task_workspace_requires_project",
        ),
        CheckConstraint(
            "artist_portal_kind IS NULL OR artist_portal_kind IN ('song', 'milestone')",
            name="ck_task_artist_portal_kind",
        ),
        CheckConstraint(
            "integration_kind IS NULL OR integration_kind = 'press_release'",
            name="ck_task_integration_kind",
        ),
        ForeignKeyConstraint(
            ["project_id", "workspace_id"],
            ["project.id", "project.workspace_id"],
            name="fk_task_project_workspace",
        ),
        ForeignKeyConstraint(
            ["task_type_id", "workspace_id"],
            ["task_type.id", "task_type.workspace_id"],
            name="fk_task_task_type_workspace",
        ),
        Index("ix_task_workspace_id", "workspace_id"),
    )
    
    project_id: Mapped[str] = mapped_column(String(50), ForeignKey("project.id"), nullable=True, default=None)
    workspace_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("workspace.id", name="fk_task_workspace"),
        nullable=True,
        default=None,
    )
    task_type_id: Mapped[str] = mapped_column(String(50), ForeignKey("task_type.id"), nullable=True, default=None)
    category_id: Mapped[str] = mapped_column(String(50), ForeignKey("task_category.id"), nullable=True, default=None)
    title: Mapped[str] = mapped_column(String(255), nullable=True, default=None)
    description: Mapped[str] = mapped_column(Text, nullable=True, default=None)
    priority: Mapped[str] = mapped_column(String(100), nullable=True, default="medium")
    status: Mapped[str] = mapped_column(String(100), nullable=True, default="pending")
    due_date: Mapped[datetime] = mapped_column(DateTime, nullable=True, default=None)
    artist_portal_kind: Mapped[str | None] = mapped_column(String(30), nullable=True)
    public_summary: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    integration_kind: Mapped[str | None] = mapped_column(String(30), nullable=True)
