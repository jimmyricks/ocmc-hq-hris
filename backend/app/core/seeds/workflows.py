"""
Seed: Workflows
===============

Creates the standard workspace task workflow once for each workspace. The
workflow intentionally includes review/revision transitions while keeping the
primary path Draft -> Pending -> For Approval -> Approved -> Done.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.framework.models.workflow import Workflow
from app.core.framework.models.workflow_action import WorkflowAction
from app.core.framework.models.workflow_state import WorkflowState, generate_slug
from app.core.framework.models.workflow_state_link import WorkflowStateLink
from app.core.framework.models.workflow_transition import WorkflowTransition
from app.core.seeds import SeedResult
from app.modules.workspaces.models import Workspace


DEFAULT_TASK_STATES: list[tuple[str, str, int, int]] = [
    # (label, color, x, y)
    ("Draft", "neutral", 0, 80),
    ("Pending", "info", 280, 80),
    ("For Approval", "warning", 560, 80),
    ("Approved", "success", 840, 80),
    ("Needs Revision", "error", 560, 280),
    ("Done", "success", 1120, 80),
]

DEFAULT_TASK_TRANSITIONS: list[tuple[str, str, str, list[str]]] = [
    ("draft", "start", "pending", ["workspace:member", "workspace:supervisor"]),
    ("pending", "submit_for_review", "for_approval", ["workspace:member"]),
    ("for_approval", "approve", "approved", ["workspace:supervisor"]),
    (
        "for_approval",
        "request_changes",
        "needs_revision",
        ["workspace:supervisor"],
    ),
    ("for_approval", "reject", "pending", ["workspace:supervisor"]),
    ("needs_revision", "submit_for_review", "for_approval", ["workspace:member"]),
    ("approved", "complete", "done", ["workspace:supervisor"]),
]


async def _ensure_state(
    db: AsyncSession, label: str, color: str
) -> tuple[WorkflowState, bool]:
    slug = generate_slug(label)
    state = await db.scalar(
        select(WorkflowState).where(WorkflowState.slug == slug)
    )
    if state:
        return state, False
    state = WorkflowState(label=label, slug=slug, color=color)
    db.add(state)
    await db.flush()
    return state, True


async def _ensure_action(db: AsyncSession, slug: str, label: str) -> tuple[WorkflowAction, bool]:
    action = await db.scalar(
        select(WorkflowAction).where(WorkflowAction.slug == slug)
    )
    if action:
        return action, False
    action = WorkflowAction(label=label, slug=slug)
    db.add(action)
    await db.flush()
    return action, True


async def _create_default_task_workflow(
    db: AsyncSession, workspace: Workspace
) -> tuple[Workflow, int]:
    workflow = Workflow(
        name="Standard Task Lifecycle",
        target_entity="task",
        workspace_id=workspace.id,
        is_active=True,
        is_default=True,
    )
    db.add(workflow)
    await db.flush()

    created_catalog_entries = 0
    state_links: dict[str, WorkflowStateLink] = {}
    for index, (label, color, x, y) in enumerate(DEFAULT_TASK_STATES):
        state, created = await _ensure_state(db, label, color)
        created_catalog_entries += int(created)
        link = WorkflowStateLink(
            workflow_id=workflow.id,
            state_id=state.id,
            is_initial=state.slug == "draft",
            sort_order=index,
        )
        link.set_visual_config({"x": x, "y": y})
        db.add(link)
        await db.flush()
        state_links[state.slug] = link

    action_labels = {
        "start": "Start",
        "submit_for_review": "Submit for Review",
        "approve": "Approve",
        "request_changes": "Request Changes",
        "reject": "Reject",
        "complete": "Complete",
    }
    for index, (from_slug, action_slug, to_slug, roles) in enumerate(
        DEFAULT_TASK_TRANSITIONS
    ):
        action, created = await _ensure_action(
            db, action_slug, action_labels[action_slug]
        )
        created_catalog_entries += int(created)
        transition = WorkflowTransition(
            from_state_link_id=state_links[from_slug].id,
            action_id=action.id,
            to_state_link_id=state_links[to_slug].id,
            sort_order=index,
        )
        transition.set_allowed_roles(roles)
        db.add(transition)

    return workflow, created_catalog_entries


async def seed_workflows(db: AsyncSession) -> SeedResult:
    """Create each workspace's default task workflow idempotently."""
    result = SeedResult(entity="Workflow")
    workspaces = (
        await db.execute(
            select(Workspace).where(Workspace.is_active == True).order_by(Workspace.name)
        )
    ).scalars().all()

    for workspace in workspaces:
        workflows = (
            await db.execute(
                select(Workflow)
                .where(
                    Workflow.workspace_id == workspace.id,
                    Workflow.target_entity == "task",
                )
                .order_by(Workflow.created_at.asc())
            )
        ).scalars().all()
        if not workflows:
            _, catalog_created = await _create_default_task_workflow(db, workspace)
            result.created += 1 + catalog_created
            continue

        default = next((item for item in workflows if item.is_default), None)
        if not default:
            active = next((item for item in workflows if item.is_active), None)
            if active:
                active.is_default = True
                result.updated += 1
            else:
                workflows[0].is_default = True
                workflows[0].is_active = True
                result.updated += 1
        else:
            result.skipped += 1

    await db.commit()
    return result
