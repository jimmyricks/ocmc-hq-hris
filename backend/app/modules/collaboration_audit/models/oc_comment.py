from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.core.base_model import BaseModel


class OcComment(BaseModel):
    """Comment entity model."""
    __tablename__ = "oc_comment"
    
    reference_entity: Mapped[str] = mapped_column(String(255), nullable=True, default=None)
    reference_id: Mapped[str] = mapped_column(String(255), nullable=True, default=None)
    comment_by: Mapped[str] = mapped_column(String(50), ForeignKey("core_users.id"), nullable=True, default=None)
    comment_text: Mapped[str] = mapped_column(Text, nullable=True, default=None)
