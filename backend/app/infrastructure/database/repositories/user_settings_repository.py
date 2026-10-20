"""
User Settings Repository
=========================
Concrete SQLAlchemy implementation for user settings data access.
Follows Clean Architecture - no business logic, only data operations.
"""
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.framework.models.user_settings import UserSettings


class UserSettingsRepository:
    """Concrete user settings repository backed by SQLAlchemy."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_user_id(self, user_id: str) -> Optional[UserSettings]:
        """Get user settings by user ID."""
        result = await self.db.execute(
            select(UserSettings).where(UserSettings.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def create_or_update(
        self,
        user_id: str,
        dashboard_field_config: Optional[dict] = None,
        dashboard_selections: Optional[dict] = None,
        theme: Optional[str] = None,
    ) -> UserSettings:
        """Create or update user settings for a user."""
        existing = await self.get_by_user_id(user_id)

        if existing:
            existing.dashboard_field_config = dashboard_field_config
            existing.dashboard_selections = dashboard_selections
            existing.theme = theme
            self.db.add(existing)
            await self.db.flush()
            await self.db.commit()
            return existing
        else:
            import uuid
            settings_id = str(uuid.uuid4())

            new_settings = UserSettings(
                id=settings_id,
                user_id=user_id,
                dashboard_field_config=dashboard_field_config,
                dashboard_selections=dashboard_selections,
                theme=theme,
            )
            self.db.add(new_settings)
            await self.db.flush()
            await self.db.commit()
            return new_settings

    async def delete(self, user_id: str) -> bool:
        """Delete user settings for a user."""
        result = await self.db.execute(
            select(UserSettings).where(UserSettings.user_id == user_id)
        )
        settings = result.scalar_one_or_none()
        if settings:
            await self.db.delete(settings)
            return True
        return False
