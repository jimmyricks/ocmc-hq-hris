from datetime import date
from sqlalchemy import Date, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.core.base_model import BaseModel


class Ledger(BaseModel):
    """Ledger entity model."""
    __tablename__ = "ledger"
    
    reference_entity: Mapped[str] = mapped_column(String(255), nullable=True, default=None)
    reference_id: Mapped[str] = mapped_column(String(255), nullable=True, default=None)
    user_id: Mapped[str] = mapped_column(String(50), ForeignKey("core_users.id"), nullable=True, default=None)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=True, default=0)
    entry_type: Mapped[str] = mapped_column(String(100), nullable=True, default=None)
    description: Mapped[str] = mapped_column(Text, nullable=True, default=None)
    period: Mapped[date] = mapped_column(Date, nullable=True, default=None)
