from sqlalchemy import Boolean, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.core.base_model import BaseModel


class TaskType(BaseModel):
    """Task Type entity model."""
    __tablename__ = "task_type"
    __table_args__ = (
        UniqueConstraint("id", "workspace_id", name="uq_task_type_id_workspace"),
    )
    
    name: Mapped[str] = mapped_column(String(255), nullable=True, default=None)
    workspace_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("workspace.id"), nullable=True, default=None, index=True
    )
    description: Mapped[str] = mapped_column(Text, nullable=True, default=None)
    unit_rate: Mapped[float] = mapped_column(Numeric(12, 2), nullable=True, default=None)
    unit: Mapped[str] = mapped_column(String(100), nullable=True, default=None)
    requires_approval: Mapped[bool] = mapped_column(Boolean, nullable=True, default=True)
