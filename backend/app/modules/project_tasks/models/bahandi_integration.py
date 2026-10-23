from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class BahandiFeedCredential(Base):
    __tablename__ = "bahandi_feed_credential"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    artist_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


class BahandiPressOutbox(Base):
    __tablename__ = "bahandi_press_outbox"
    __table_args__ = (
        UniqueConstraint("source_task_id", name="uq_bahandi_press_outbox_task"),
        CheckConstraint(
            "status IN ('queued', 'processing', 'retrying', 'completed', 'failed')",
            name="ck_bahandi_press_outbox_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_task_id: Mapped[str] = mapped_column(String(50), nullable=False)
    source_submission_id: Mapped[str] = mapped_column(String(50), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued", index=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    run_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_error: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
