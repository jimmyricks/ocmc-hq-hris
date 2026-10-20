from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import BaseModel


class WorkspaceTeam(BaseModel):
    __tablename__ = "workspace_team"
    __table_args__ = (
        UniqueConstraint("workspace_id", "slug", name="uq_workspace_team_slug"),
    )

    workspace_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("workspace.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False)
    head_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("core_users.id"), nullable=True
    )
