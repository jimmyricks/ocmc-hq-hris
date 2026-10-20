from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column
from app.core.base_model import BaseModel


class Workspace(BaseModel):
    """Workspace entity model."""
    __tablename__ = "workspace"
    
    name: Mapped[str] = mapped_column(String(255), nullable=True, default=None)
    slug: Mapped[str] = mapped_column(String(255), nullable=True, default=None)
    color: Mapped[str] = mapped_column(String(255), nullable=True, default=None)
    timezone: Mapped[str] = mapped_column(String(255), nullable=True, default=None)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=True, default=True)
