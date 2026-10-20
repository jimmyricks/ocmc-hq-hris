from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.core.base_model import BaseModel


class OcAuditLog(BaseModel):
    """Audit Log entity model."""
    __tablename__ = "oc_audit_log"
    
    reference_entity: Mapped[str] = mapped_column(String(255), nullable=True, default=None)
    reference_id: Mapped[str] = mapped_column(String(255), nullable=True, default=None)
    action: Mapped[str] = mapped_column(String(100), nullable=True, default=None)
    old_values: Mapped[str] = mapped_column(Text, nullable=True, default=None)
    new_values: Mapped[str] = mapped_column(Text, nullable=True, default=None)
    actor_id: Mapped[str] = mapped_column(String(50), ForeignKey("core_users.id"), nullable=True, default=None)
    ip_address: Mapped[str] = mapped_column(String(255), nullable=True, default=None)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=True, default=None)
