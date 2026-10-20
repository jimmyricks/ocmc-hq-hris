from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column
from app.core.base_model import BaseModel


class Workspace(BaseModel):
    """Workspace entity model."""
    __tablename__ = "workspace"
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    color: Mapped[str] = mapped_column(String(7), nullable=False)
    timezone: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
