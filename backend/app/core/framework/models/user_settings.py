from sqlalchemy import String, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.core.base_model import BaseModel


class UserSettings(BaseModel):
    """User settings for dashboard preferences and UI customization."""
    __tablename__ = "user_settings"

    user_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, index=True)

    # Dashboard preferences
    # Legacy columns kept nullable for DB compatibility; no longer used by application code
    dashboard_card_filter: Mapped[str | None] = mapped_column(
        String(50),
        default=None,
        nullable=True,
    )
    dashboard_card_type: Mapped[str | None] = mapped_column(
        String(50),
        default=None,
        nullable=True,
    )
    dashboard_field_config: Mapped[dict | None] = mapped_column(
        JSON,
        default=None,
        nullable=True
    )
    
    # Selected workflow states and charts per dashboard (max 4 each)
    # Format: {"work-management": {"states": ["Requested", "In Progress"], "charts": ["Work Order Status"]}}
    dashboard_selections: Mapped[dict | None] = mapped_column(
        JSON,
        default=None,
        nullable=True
    )
    
    # UI preferences (for future use)
    theme: Mapped[str | None] = mapped_column(String(50), default=None, nullable=True)
