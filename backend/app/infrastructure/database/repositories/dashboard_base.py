"""
Dashboard Repository Base (Infrastructure Layer)
=================================================
Shared utilities for dashboard repository implementations.
"""
from datetime import date, timedelta
from typing import Any, Optional

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.framework.models.workflow import Workflow
from app.core.framework.models.workflow_state import WorkflowState


class DashboardRepoBase:
    """Base class with shared SQL utilities for dashboard repositories."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_workflow_state_labels(self) -> dict[str, str]:
        """Fetch workflow state labels for consistent naming."""
        result = await self.db.execute(select(WorkflowState.slug, WorkflowState.label))
        return {row.slug: row.label for row in result.fetchall()}

    @staticmethod
    def _build_timestamp_date_filter(
        column_name: str,
        start_date: Optional[date],
        end_date: Optional[date],
    ) -> tuple[str, dict[str, Any]]:
        clauses: list[str] = []
        params: dict[str, Any] = {}
        if start_date:
            clauses.append(f"{column_name} >= :start_date")
            params["start_date"] = start_date
        if end_date:
            clauses.append(f"{column_name} < :end_date_exclusive")
            params["end_date_exclusive"] = end_date + timedelta(days=1)

        if not clauses:
            return "", params

        return " AND " + " AND ".join(clauses), params

    @staticmethod
    def _merge_count(bucket: dict[str, int], label: str, count: int) -> None:
        bucket[label] = bucket.get(label, 0) + count

    def _build_card_filter_clause(
        self, card_filter: str, user_id: Optional[str], table_alias: str = ""
    ) -> tuple[str, dict[str, Any]]:
        """Build SQL filter clause based on card filter preference."""
        alias = f"{table_alias}." if table_alias else ""
        clauses: list[str] = []
        params: dict[str, Any] = {}

        if card_filter == "my_records" and user_id:
            clauses.append(f"{alias}created_by = :card_filter_user_id")
            params["card_filter_user_id"] = user_id
        elif card_filter == "overdue":
            clauses.append(f"{alias}due_date < CURRENT_DATE")
            clauses.append(f"LOWER(COALESCE({alias}workflow_state, '')) != 'closed'")

        if not clauses:
            return "", params
        return " AND " + " AND ".join(clauses), params
