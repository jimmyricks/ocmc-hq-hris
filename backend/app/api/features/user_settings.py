"""
User Settings API Endpoints
============================
REST API for user preferences management.
"""
from typing import Optional
from fastapi import APIRouter, Depends, Header, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, get_user_settings_service, get_current_user_from_token
from app.application.services.user_settings_service import UserSettingsService
from app.application.services.dashboards.config import (
    DASHBOARD_DEFINITIONS,
    DASHBOARD_ENTITY_MAP,
    get_entity_dashboard_options,
)

router = APIRouter(prefix="/user-settings", tags=["user-settings"])


class DashboardPreferencesUpdate(BaseModel):
    """Request model for updating dashboard preferences."""
    field_config: Optional[dict] = None
    dashboard_selections: Optional[dict] = None


class ThemeUpdate(BaseModel):
    """Request model for updating theme preference."""
    theme: Optional[str] = None


@router.get("/dashboard")
async def get_dashboard_settings(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
    user_settings_service: UserSettingsService = Depends(get_user_settings_service),
):
    """Get current user's dashboard settings."""
    current_user = await get_current_user_from_token(authorization, db)
    user_settings_service.current_user = current_user
    settings = await user_settings_service.get_user_settings()
    
    if not settings:
        # Return default settings if none exist
        return {
            "dashboard_field_config": None,
            "dashboard_selections": None,
            "theme": None,
        }

    return {
        "dashboard_field_config": settings.dashboard_field_config,
        "dashboard_selections": settings.dashboard_selections,
        "theme": settings.theme,
    }


@router.put("/dashboard/preferences")
async def update_dashboard_preferences(
    preferences: DashboardPreferencesUpdate,
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
    user_settings_service: UserSettingsService = Depends(get_user_settings_service),
):
    """Update user's dashboard preferences."""
    current_user = await get_current_user_from_token(authorization, db)
    user_settings_service.current_user = current_user

    settings = await user_settings_service.update_dashboard_preferences(
        field_config=preferences.field_config,
        dashboard_selections=preferences.dashboard_selections,
    )

    return {
        "dashboard_field_config": settings.dashboard_field_config,
        "dashboard_selections": settings.dashboard_selections,
    }


@router.put("/theme")
async def update_theme(
    theme_update: ThemeUpdate,
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
    user_settings_service: UserSettingsService = Depends(get_user_settings_service),
):
    """Update user's theme preference."""
    current_user = await get_current_user_from_token(authorization, db)
    user_settings_service.current_user = current_user
    
    settings = await user_settings_service.update_theme(theme_update.theme)
    
    return {
        "theme": settings.theme,
    }


@router.get("/dashboard-options")
async def get_dashboard_options(
    dashboard_key: str = Query(..., description="Dashboard key (e.g., work-management, procurement)"),
):
    """Get available dashboard checkbox options for a dashboard."""
    if dashboard_key not in DASHBOARD_DEFINITIONS:
        return {"error": "Invalid dashboard key"}
    
    entity_name = DASHBOARD_ENTITY_MAP.get(dashboard_key)
    entity_options = get_entity_dashboard_options(entity_name) if entity_name else {}
    
    show_options = []
    # Record states
    for state in entity_options.get("states", []):
        show_options.append({
            "value": f"state:{state}",
            "label": state,
            "type": "state",
        })
    # Special filters
    show_options.append({"value": "my_records", "label": "My Records", "type": "filter"})
    show_options.append({"value": "upcoming", "label": "Upcoming", "type": "filter"})
    show_options.append({"value": "overdue", "label": "Overdue", "type": "filter"})
    
    group_options = []
    # Total by states
    group_options.append({
        "value": "total_by_states",
        "label": "Total Records Divided by States",
        "type": "group",
    })
    # By fields
    for field in entity_options.get("fields", []):
        group_options.append({
            "value": f"field:{field['value']}",
            "label": f"By {field['label']}",
            "type": "field",
            "field_type": field.get("type"),
        })
    
    return {
        "show_options": show_options,
        "group_options": group_options,
    }
