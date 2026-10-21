from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.core.base_model import BaseModel


class Invoice(BaseModel):
    """Invoice entity model."""
    __tablename__ = "invoice"
    __table_args__ = (
        UniqueConstraint("payroll_entry_id", name="uq_invoice_payroll_entry_id"),
    )
    
    invoice_number: Mapped[str] = mapped_column(String(255), nullable=True, default=None)
    payroll_entry_id: Mapped[str] = mapped_column(String(50), ForeignKey("payroll_entry.id"), nullable=True, default=None)
    payroll_period_id: Mapped[str] = mapped_column(String(50), ForeignKey("payroll_period.id"), nullable=True, default=None)
    user_id: Mapped[str] = mapped_column(String(50), ForeignKey("core_users.id"), nullable=True, default=None)
    total_tasks: Mapped[int] = mapped_column(Integer, nullable=True, default=None)
    total_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=True, default=None)
    currency: Mapped[str] = mapped_column(String(100), nullable=True, default="PHP")
    status: Mapped[str] = mapped_column(String(100), nullable=True, default="issued")
    issued_at: Mapped[datetime] = mapped_column(DateTime, nullable=True, default=None)
    paid_at: Mapped[datetime] = mapped_column(DateTime, nullable=True, default=None)
