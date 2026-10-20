from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column
from app.core.base_model import BaseModel


class PayrollEntry(BaseModel):
    """Payroll Entry entity model."""
    __tablename__ = "payroll_entry"
    
    payroll_period_id: Mapped[str] = mapped_column(String(50), ForeignKey("payroll_period.id"), nullable=True, default=None)
    user_id: Mapped[str] = mapped_column(String(50), ForeignKey("core_users.id"), nullable=True, default=None)
    total_tasks: Mapped[int] = mapped_column(Integer, nullable=True, default=0)
    total_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=True, default=0)
    status: Mapped[str] = mapped_column(String(100), nullable=True, default="draft")
    generated_at: Mapped[datetime] = mapped_column(DateTime, nullable=True, default=None)
    approved_by: Mapped[str] = mapped_column(String(50), ForeignKey("core_users.id"), nullable=True, default=None)
    approved_at: Mapped[datetime] = mapped_column(DateTime, nullable=True, default=None)
