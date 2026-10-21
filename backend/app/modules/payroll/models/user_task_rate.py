from sqlalchemy import CheckConstraint, ForeignKey, Index, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import BaseModel


class UserTaskRate(BaseModel):
    """Workspace-scoped employee override for a task type's default rate."""

    __tablename__ = "user_task_rate"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "task_type_id",
            "user_id",
            name="uq_user_task_rate_workspace_type_user",
        ),
        CheckConstraint("rate > 0", name="ck_user_task_rate_positive"),
        Index("ix_user_task_rate_user_workspace", "user_id", "workspace_id"),
    )

    workspace_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("workspace.id"), nullable=False, index=True
    )
    task_type_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("task_type.id"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("core_users.id"), nullable=False, index=True
    )
    rate: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
