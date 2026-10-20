"""
User Settings Service (Application Layer)
=========================================
CLEAN architecture-compliant user settings service.

Orchestrates user settings operations.
Delegates data access to UserSettingsRepository.

Architecture:
- Application Layer: UserSettingsService (orchestration, business logic)
- Infrastructure Layer: UserSettingsRepository (data access, SQL queries)
- No infrastructure coupling (no AsyncSession, no raw SQL in service)
"""
from typing import Optional
from app.core.security import CurrentUser
from app.infrastructure.database.repositories.user_settings_repository import UserSettingsRepository
from app.core.framework.models.user_settings import UserSettings


class UserSettingsService:
    """
    Application-layer user settings orchestration.

    Handles user preferences for dashboard and UI customization.
    Delegates all data access to UserSettingsRepository.
    """

    def __init__(
        self,
        user_settings_repo: UserSettingsRepository,
        current_user: CurrentUser,
    ) -> None:
        self._user_settings_repo = user_settings_repo
        self.current_user = current_user

    async def get_user_settings(self) -> Optional[UserSettings]:
        """Get current user's settings."""
        return await self._user_settings_repo.get_by_user_id(self.current_user.id)

    async def update_dashboard_preferences(
        self,
        field_config: Optional[dict] = None,
        dashboard_selections: Optional[dict] = None,
    ) -> UserSettings:
        """
        Update user's dashboard preferences.

        Args:
            field_config: Optional field configuration for by_fields type
            dashboard_selections: Selected show options and group options per dashboard
        """
        return await self._user_settings_repo.create_or_update(
            user_id=self.current_user.id,
            dashboard_field_config=field_config,
            dashboard_selections=dashboard_selections,
        )

    async def update_theme(self, theme: Optional[str]) -> UserSettings:
        """Update user's theme preference."""
        existing = await self._user_settings_repo.get_by_user_id(self.current_user.id)
        if existing:
            return await self._user_settings_repo.create_or_update(
                user_id=self.current_user.id,
                dashboard_field_config=existing.dashboard_field_config,
                dashboard_selections=existing.dashboard_selections,
                theme=theme,
            )
        else:
            return await self._user_settings_repo.create_or_update(
                user_id=self.current_user.id,
                theme=theme,
            )
