from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.core.base_model import BaseModel


class ShortLinkClick(BaseModel):
    """Short Link Click entity model."""
    __tablename__ = "short_link_click"
    
    short_link_id: Mapped[str] = mapped_column(String(50), ForeignKey("short_link.id"), nullable=True, default=None)
    clicked_at: Mapped[datetime] = mapped_column(DateTime, nullable=True, default=None)
    ip_hash: Mapped[str] = mapped_column(String(255), nullable=True, default=None)
    user_agent: Mapped[str] = mapped_column(Text, nullable=True, default=None)
    referer: Mapped[str] = mapped_column(Text, nullable=True, default=None)
    country: Mapped[str] = mapped_column(String(255), nullable=True, default=None)
