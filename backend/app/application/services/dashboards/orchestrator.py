"""
Dashboard Orchestrator (Application Layer)
===========================================

Coordinates dashboard data assembly.  In the barebones backend this is a
no-op placeholder that preserves the interface used by the authentication
endpoint and other callers.

Original responsibilities:
  - Compose dashboard config, widget handlers, stats calculator, and data fetcher
  - Return assembled payload for the current user

Re-implementation can reintroduce the component classes later.
"""
from typing import Any, Optional


class DashboardOrchestrator:
    """Stub dashboard orchestrator."""

    def __init__(
        self,
        dashboard_repo,
        current_user,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        dashboard_key: Optional[str] = None,
        selections: Optional[dict] = None,
    ) -> None:
        self._repo = dashboard_repo
        self.current_user = current_user
        self.dashboard_key = dashboard_key
        self.selections = selections or {}

    def resolve_user_widgets(self) -> list[dict]:
        """Return widgets the user is allowed to see."""
        return []

    async def get_work_order_summary(self) -> dict[str, Any]:
        return {}

    async def get_purchase_request_summary(self) -> dict[str, Any]:
        return {}

    async def get_inventory_summary(self) -> dict[str, Any]:
        return {}

    async def get_role_based_dashboard(self, dashboard_key: Optional[str] = None) -> dict[str, Any]:
        return {"dashboards": []}

    async def get_dashboard_widgets(self) -> dict[str, Any]:
        return {"widgets": []}
