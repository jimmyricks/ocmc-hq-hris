from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column
from app.core.base_model import BaseModel


class Department(BaseModel):
    """Department entity model."""
    __tablename__ = "department"
    
    name: Mapped[str] = mapped_column(String(255), nullable=True, default=None)
    head_user_id: Mapped[str] = mapped_column(String(50), ForeignKey("core_users.id"), nullable=True, default=None)
