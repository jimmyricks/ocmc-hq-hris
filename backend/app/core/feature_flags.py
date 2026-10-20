"""
Core Layer: Feature Flags

Runtime feature toggles (e.g., Purchase Order module).

Clean Architecture Layer: Core
Responsibility: Provide feature flag access helpers
"""
from app.core.config import settings


# PO entities that should be hidden when PO is disabled
PO_ENTITIES = frozenset({"purchase_order", "purchase_order_line"})

# Actions on other entities that should be hidden when PO is disabled
PO_DEPENDENT_ACTIONS = frozenset({"create_purchase_order"})


def is_po_enabled() -> bool:
    """Return True if the Purchase Order workflow is enabled."""
    return settings.PURCHASE_ORDER_ENABLED
