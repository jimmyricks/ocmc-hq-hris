from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.core.base_model import BaseModel


class QrCode(BaseModel):
    """QR Code entity model."""
    __tablename__ = "qr_code"
    
    source_type: Mapped[str] = mapped_column(String(100), nullable=True, default="url")
    source_value: Mapped[str] = mapped_column(Text, nullable=True, default=None)
    short_link_id: Mapped[str] = mapped_column(String(50), ForeignKey("short_link.id"), nullable=True, default=None)
    error_correction_level: Mapped[str] = mapped_column(String(100), nullable=True, default="M")
    size: Mapped[int] = mapped_column(Integer, nullable=True, default=256)
    format: Mapped[str] = mapped_column(String(100), nullable=True, default="svg")
    fg_color: Mapped[str] = mapped_column(String(255), nullable=True, default="#000000")
    bg_color: Mapped[str] = mapped_column(String(255), nullable=True, default="#ffffff")
