from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.core.base_model import BaseModel


class Notification(BaseModel):
    """Notification entity model."""
    __tablename__ = "notification"
    
    user_id: Mapped[str] = mapped_column(String(50), ForeignKey("core_users.id"), nullable=True, default=None)
    reference_entity: Mapped[str] = mapped_column(String(255), nullable=True, default=None)
    reference_id: Mapped[str] = mapped_column(String(255), nullable=True, default=None)
    type: Mapped[str] = mapped_column(String(100), nullable=True, default=None)
    message: Mapped[str] = mapped_column(Text, nullable=True, default=None)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=True, default=False)
