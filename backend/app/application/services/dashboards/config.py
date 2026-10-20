"""
Dashboard Configuration Provider
=================================

Previously defined per-dashboard widget configurations for EAM domains
(work-management, procurement, inventory).  In the barebones backend the
configuration is empty, but the structure is preserved so callers such as
``api/system/auth.py`` can continue to import and use the provider.

Add new dashboard definitions here when business modules are reintroduced.
"""
from typing import Optional


# Dashboard definitions: key -> {label, stats, charts, ...}
DASHBOARD_DEFINITIONS: dict[str, dict] = {}

# Ordered list of dashboard keys for the UI
DASHBOARD_ORDER: list[str] = []

# Map widget type to dashboard key
WIDGET_DASHBOARD_MAP: dict[str, str] = {}

# Map dashboard key to primary entity name
DASHBOARD_ENTITY_MAP: dict[str, str] = {}


def get_entity_dashboard_options(entity_name: str) -> list[dict]:
    """Return dashboard options for an entity."""
    return []


class DashboardConfigProvider:
    """Provides dashboard configuration without business logic."""

    def __init__(self):
        pass

    @staticmethod
    def resolve_allowed_dashboard_keys(widget_types: list[str], is_superuser: bool) -> list[str]:
        """Return allowed dashboard keys for the given widget types."""
        return []

    @staticmethod
    def build_allowed_dashboards_list(allowed_keys: list[str]) -> list[dict]:
        """Build list of dashboard metadata for allowed keys."""
        return []
