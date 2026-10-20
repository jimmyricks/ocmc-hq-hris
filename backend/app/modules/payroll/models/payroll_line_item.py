from sqlalchemy import Float, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column
from app.core.base_model import BaseModel


class PayrollLineItem(BaseModel):
    """Payroll Line Item entity model."""
    __tablename__ = "payroll_line_item"
    
    payroll_entry_id: Mapped[str] = mapped_column(String(50), ForeignKey("payroll_entry.id"), nullable=True, default=None)
    idx: Mapped[int] = mapped_column(Integer, nullable=True, default=0)
    task_submission_id: Mapped[str] = mapped_column(String(50), ForeignKey("task_submission.id"), nullable=True, default=None)
    workspace_id: Mapped[str] = mapped_column(String(50), ForeignKey("workspace.id"), nullable=True, default=None)
    rate: Mapped[float] = mapped_column(Numeric(12, 2), nullable=True, default=None)
    quantity: Mapped[float] = mapped_column(Float, nullable=True, default=1)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=True, default=0)
