"""
Seed: Workflow States
=====================
Full canonical catalog of 38 workflow states with Nuxt UI semantic color mappings.
Sourced from: reset_workflow_catalog.py (36 states) + additional EAM states.
Idempotent — skips existing states by slug.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.seeds import SeedResult
from app.core.framework.models.workflow_state import WorkflowState, generate_slug

# (label, nuxt-ui color)
# Nuxt UI semantic colors: success, primary, error, warning, neutral, info
WORKFLOW_STATES: list[tuple[str, str]] = [
    # Drafting / Initial
    ("Draft",               "neutral"),
    ("Open",                "info"),
    ("Requested",           "info"),
    ("Submitted",           "neutral"),

    # Approval flow
    ("Pending Approval",    "neutral"),
    ("Pending Review",      "neutral"),
    ("Review",              "neutral"),
    ("Approved",            "success"),
    ("Rejected",            "error"),

    # Sourcing / Purchasing
    ("Sourcing",            "neutral"),
    ("Awarded",             "neutral"),
    ("Ordered",             "neutral"),
    ("Posted",              "success"),
    ("Release",             "neutral"),
    ("Planned",             "neutral"),

    # Receiving
    ("Partially Received",  "warning"),
    ("Fully Received",      "success"),
    ("Received",            "neutral"),
    ("Returned",            "neutral"),
    ("Issued",              "neutral"),

    # Work / Maintenance flow
    ("Ready",               "neutral"),
    ("In Progress",         "warning"),
    ("Awaiting Resources",  "warning"),
    ("On Hold",             "neutral"),
    ("Completed",           "success"),
    ("Complete",            "success"),
    ("Closed",              "neutral"),
    ("Cancelled",           "error"),

    # Stock
    ("Sourcing",            "neutral"),  # duplicate handled by idempotency

    # Asset lifecycle
    ("Acquired",            "success"),
    ("Inspected",           "success"),
    ("Failed Inspection",   "error"),
    ("Active",              "primary"),
    ("Inactive",            "neutral"),
    ("Under Maintenance",   "warning"),
    ("Under Repair",        "warning"),
    ("Decommissioned",      "error"),
    ("Disposed",            "error"),
]


async def seed_workflow_states(db: AsyncSession) -> SeedResult:
    """Create canonical workflow states. Deduplicates by slug — updates existing colors."""
    result = SeedResult(entity="WorkflowState")
    seen_slugs: set[str] = set()

    for label, color in WORKFLOW_STATES:
        slug = generate_slug(label)
        if slug in seen_slugs:
            continue  # de-duplicate within list
        seen_slugs.add(slug)

        existing = await db.execute(
            select(WorkflowState).where(WorkflowState.slug == slug)
        )
        state = existing.scalar_one_or_none()
        
        if state:
            # Update existing state's color
            if state.color != color:
                state.color = color
                result.updated += 1
            else:
                result.skipped += 1
        else:
            # Create new state
            db.add(WorkflowState(label=label, slug=slug, color=color))
            result.created += 1

    await db.commit()
    return result
