"""
Seed: Workflows
===============

Previously created workflow configurations for EAM entities (asset, purchase_request,
purchase_order, maintenance_request, work_order, etc.).

This file is retained as a placeholder for the workflow seeding pipeline.
The core workflow engine remains functional; new workflow definitions can be
seeded here when business modules are re-added.

Expected function signature:
    async def seed_workflows(db: AsyncSession) -> SeedResult

The seed result is reported by ``core/seeds/__init__.py``.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.seeds import SeedResult


async def seed_workflows(db: AsyncSession) -> SeedResult:
    """No-op workflow seed for the barebones backend."""
    return SeedResult(entity="Workflow", created=0, skipped=0)
