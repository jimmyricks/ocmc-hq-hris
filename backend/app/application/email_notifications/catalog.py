"""
Developer-maintained list of email notifications users may subscribe to.

In the barebones backend the catalog is empty; the notification infrastructure
(core NotificationSubscription, EmailNotificationService, dispatcher) remains
functional.

Adding a notification:
    1. Define a NotificationCatalogEntry below
    2. Expose it through _build_catalog()
    3. Dispatch via ``EmailNotificationDispatcher.notify(catalog_id, record)``
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class NotificationCatalogEntry:
    catalog_id: str
    title: str
    description: str
    entity_type: str
    event: str
    category: str = "General"


def _build_catalog() -> tuple[NotificationCatalogEntry, ...]:
    """Build the notification catalog."""
    rows: list[NotificationCatalogEntry] = []
    return tuple(rows)


_CATALOG: tuple[NotificationCatalogEntry, ...] = _build_catalog()
_BY_ID: dict[str, NotificationCatalogEntry] = {e.catalog_id: e for e in _CATALOG}

CATALOG_ID_CREATED: dict[str, str] = {}


def list_catalog_entries() -> list[NotificationCatalogEntry]:
    return list(_CATALOG)


def get_catalog_entry(catalog_id: str) -> Optional[NotificationCatalogEntry]:
    return _BY_ID.get(catalog_id)


def require_catalog_entry(catalog_id: str) -> NotificationCatalogEntry:
    entry = get_catalog_entry(catalog_id)
    if not entry:
        raise ValueError(f"Unknown notification catalog_id: {catalog_id}")
    return entry


def is_catalog_entity_event(entity_type: str, event: str) -> bool:
    return any(e.entity_type == entity_type and e.event == event for e in _CATALOG)


def catalog_id_for_routing(entity_type: str, event: str) -> Optional[str]:
    for e in _CATALOG:
        if e.entity_type == entity_type and e.event == event:
            return e.catalog_id
    return None
