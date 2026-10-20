from datetime import datetime
from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.core.base_model import BaseModel


class ShortLink(BaseModel):
    """Short Link entity model."""
    __tablename__ = "short_link"
    
    slug: Mapped[str] = mapped_column(String(255), nullable=True, unique=True, default=None)
    destination_url: Mapped[str] = mapped_column(Text, nullable=True, default=None)
    title: Mapped[str] = mapped_column(String(255), nullable=True, default=None)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=True, default=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=True, default=None)
    password_hash: Mapped[str] = mapped_column(Text, nullable=True, default=None)
    show_preview: Mapped[bool] = mapped_column(Boolean, nullable=True, default=False)
    click_count: Mapped[int] = mapped_column(Integer, nullable=True, default=0)
