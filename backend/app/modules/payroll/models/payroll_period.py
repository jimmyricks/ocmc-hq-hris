from datetime import date
from sqlalchemy import Boolean, Date, String
from sqlalchemy.orm import Mapped, mapped_column
from app.core.base_model import BaseModel


class PayrollPeriod(BaseModel):
    """Payroll Period entity model."""
    __tablename__ = "payroll_period"
    
    label: Mapped[str] = mapped_column(String(255), nullable=True, default=None)
    period_type: Mapped[str] = mapped_column(String(100), nullable=True, default="bi_monthly")
    start_date: Mapped[date] = mapped_column(Date, nullable=True, default=None)
    end_date: Mapped[date] = mapped_column(Date, nullable=True, default=None)
    cutoff: Mapped[date] = mapped_column(Date, nullable=True, default=None)
    status: Mapped[str] = mapped_column(String(100), nullable=True, default="open")
    is_auto_generated: Mapped[bool] = mapped_column(Boolean, nullable=True, default=False)
