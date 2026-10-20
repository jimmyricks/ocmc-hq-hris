from sqlalchemy import Boolean, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column
from app.core.base_model import BaseModel


class PayrollSettings(BaseModel):
    """Payroll Settings entity model."""
    __tablename__ = "payroll_settings"
    
    currency: Mapped[str] = mapped_column(String(100), nullable=True, default="PHP")
    cutoff_rule: Mapped[str] = mapped_column(String(100), nullable=True, default="bi_monthly")
    default_period_start_day: Mapped[int] = mapped_column(Integer, nullable=True, default=1)
    default_period_end_day: Mapped[int] = mapped_column(Integer, nullable=True, default=15)
    auto_approve_threshold: Mapped[float] = mapped_column(Numeric(12, 2), nullable=True, default=0)
    require_hr_approval: Mapped[bool] = mapped_column(Boolean, nullable=True, default=True)
    notify_users_on_payment: Mapped[bool] = mapped_column(Boolean, nullable=True, default=True)
