"""
Dashboard Repository Facade (Infrastructure Layer)
====================================================
Backward-compatible facade for dashboard data access.

In the barebones backend no domain-specific dashboard repositories remain.
This stub preserves the interface used by dependency injection and the
DashboardOrchestrator.
"""
from sqlalchemy.ext.asyncio import AsyncSession


class DashboardRepository:
    """Stub dashboard repository."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_work_order_summary(self, start_date=None, end_date=None, user_id=None):
        return {}

    async def get_work_order_attention_list(self, limit=10):
        return []

    async def get_work_order_type_distribution(self, start_date=None, end_date=None):
        return {}

    async def get_maintenance_summary(self, start_date=None, end_date=None):
        return {}

    async def get_purchase_request_summary(self, start_date=None, end_date=None, user_id=None):
        return {}

    async def get_purchase_request_attention_list(self, limit=10):
        return []

    async def get_inventory_summary(self, threshold=10):
        return {}

    async def get_inventory_low_stock(self, threshold=10, limit=10):
        return []

    async def get_stock_count_summary(self):
        return {}

    async def get_pending_approvals(self, user_roles, limit=10, dashboard_key=None):
        return {"total": 0, "by_entity": {}}

    async def get_entity_field_distribution(self, entity_name, field_name, start_date=None, end_date=None, date_field="created_at"):
        return {"total": 0, f"by_{field_name}": {}}
