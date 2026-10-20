"""
Seed: Workflow Actions
======================
Full canonical catalog of workflow actions (verbs users can trigger).
Sourced from: reset_workflow_catalog.py (40+ actions).
Idempotent — skips existing actions by slug.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.seeds import SeedResult
from app.core.framework.models.workflow_action import WorkflowAction, generate_slug

WORKFLOW_ACTIONS: list[str] = [
    # Generic approval
    "Approve",
    "Reject",
    "Submit",
    "Submit for Approval",
    "Submit for Emergency",
    "Submit for Resolution",
    "Submit for Review",
    "Reopen",
    "Cancel",
    "Close",

    # Line-level (PO / PR)
    "Approve Line",
    "Reject Line",
    "Reject Purchase Request",
    "Revise Purchase Request",

    # Purchasing / Receiving
    "Receive All Items",
    "Receive Partial Items",
    "Create Purchase Order",
    "Award",
    "Submit Source",
    "Post",
    "Add Line Item",

    # Stores / Inventory
    "Return Item",
    "Issue Item",
    "Start Stock Count",
    "Allocate",

    # Work / Maintenance
    "Start",
    "Start Activity",
    "Complete",
    "Put On Hold",
    "Resume",

    # Asset lifecycle
    "Inspect Asset",
    "Failed Inspection",
    "Putaway",
    "Install Asset",
    "Commission",
    "Maintain Asset",
    "Decommission",
    "Issue Equipment",
    "Retire Asset",
    "Internal Repair",
    "Send to Vendor",
    "Remove Asset",
    "Finish Repair",
    "Dispose",
    "Recommission",

    # Misc
    "Activate",
    "Deactivate",
]


async def seed_workflow_actions(db: AsyncSession) -> SeedResult:
    """Create canonical workflow actions. Deduplicates by slug — skips existing."""
    result = SeedResult(entity="WorkflowAction")
    seen_slugs: set[str] = set()

    for label in WORKFLOW_ACTIONS:
        slug = generate_slug(label)
        if slug in seen_slugs:
            continue
        seen_slugs.add(slug)

        existing = await db.execute(
            select(WorkflowAction).where(WorkflowAction.slug == slug)
        )
        if existing.scalar_one_or_none():
            result.skipped += 1
            continue

        db.add(WorkflowAction(label=label, slug=slug))
        result.created += 1

    await db.commit()
    return result
