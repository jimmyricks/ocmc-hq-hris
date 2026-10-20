"""
Workflow Repository
====================
Concrete SQLAlchemy implementation for workflow data access.
"""
from typing import Any, Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.constants.permissions import can_act_on_transition
from app.core.framework.models.workflow import Workflow
from app.core.framework.models.workflow_state import WorkflowState, generate_slug
from app.core.framework.models.workflow_action import WorkflowAction
from app.core.framework.models.workflow_state_link import WorkflowStateLink
from app.core.framework.models.workflow_transition import WorkflowTransition


class WorkflowRepository:
    """Concrete workflow repository backed by SQLAlchemy."""

    def __init__(self, db: AsyncSession):
        self.db = db

    def _get_workflow_transitions(self, workflow: Workflow) -> list[WorkflowTransition]:
        """Collect all unique transitions from a workflow's state links."""
        transitions = []
        seen_ids = set()
        for state_link in workflow.state_links:
            for transition in state_link.outgoing_transitions:
                if transition.id not in seen_ids:
                    transitions.append(transition)
                    seen_ids.add(transition.id)
        return transitions

    async def get_workflow(self, entity: str) -> Optional[Workflow]:
        result = await self.db.execute(
            select(Workflow)
            .where(Workflow.target_entity == entity, Workflow.is_active == True)
            .options(
                selectinload(Workflow.state_links).selectinload(WorkflowStateLink.state),
                selectinload(Workflow.state_links)
                .selectinload(WorkflowStateLink.outgoing_transitions)
                .selectinload(WorkflowTransition.from_state_link)
                .selectinload(WorkflowStateLink.state),
                selectinload(Workflow.state_links)
                .selectinload(WorkflowStateLink.outgoing_transitions)
                .selectinload(WorkflowTransition.to_state_link)
                .selectinload(WorkflowStateLink.state),
                selectinload(Workflow.state_links)
                .selectinload(WorkflowStateLink.outgoing_transitions)
                .selectinload(WorkflowTransition.action_ref),
            )
        )
        return result.scalar_one_or_none()

    async def get_initial_state(self, entity: str) -> Optional[str]:
        workflow = await self.get_workflow(entity)
        if not workflow:
            return None
        initial_link = next((sl for sl in workflow.state_links if sl.is_initial), None)
        return initial_link.state.slug if initial_link else None

    async def get_available_actions(
        self,
        entity: str,
        current_state: str,
        user: Any = None,
        record_id: str = None,
    ) -> list[dict[str, Any]]:
        workflow = await self.get_workflow(entity)
        if not workflow:
            return []
        user_roles = set(getattr(user, 'roles', []) or []) if user else set()
        is_super = 'SystemManager' in user_roles if user_roles else False
        
        # Fetch entity record to check ownership if record_id is provided
        doc = None
        if record_id:
            from app.infrastructure.database.repositories.entity_repository import get_entity_model
            model = get_entity_model(entity)
            if model:
                result = await self.db.execute(select(model).where(model.id == record_id))
                doc = result.scalar_one_or_none()
        
        available = []
        for t in self._get_workflow_transitions(workflow):
            if t.from_state_link.state.slug == current_state:
                roles = t.get_allowed_roles()
                if is_super or can_act_on_transition(
                    roles,
                    list(user_roles),
                    created_by=str(doc.created_by) if doc else "",
                    current_user_id=str(user.id),
                ):
                    available.append({
                        "action_slug": t.action_ref.slug,
                        "action_label": t.action_ref.label,
                        "to_state_slug": t.to_state_link.state.slug,
                        "to_state_label": t.to_state_link.state.label,
                    })
        return available

    async def validate_transition(
        self,
        entity: str,
        current_state: str,
        action: str,
        user: Any = None,
        record_id: str = None,
        workflow: Optional[Workflow] = None,
        doc: Any = None,
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        if workflow is None:
            workflow = await self.get_workflow(entity)
        if not workflow:
            return False, None, f"No workflow found for entity '{entity}'"
        user_roles = set(getattr(user, 'roles', []) or []) if user else set()
        is_super = 'SystemManager' in user_roles if user_roles else False
        
        # Fetch entity record to check ownership if record_id is provided
        if doc is None and record_id:
            from app.infrastructure.database.repositories.entity_repository import get_entity_model
            model = get_entity_model(entity)
            if model:
                result = await self.db.execute(select(model).where(model.id == record_id))
                doc = result.scalar_one_or_none()
        
        for t in self._get_workflow_transitions(workflow):
            if t.from_state_link.state.slug == current_state and t.action_ref.slug == action:
                roles = t.get_allowed_roles()
                if is_super or can_act_on_transition(
                    roles,
                    list(user_roles),
                    created_by=str(doc.created_by) if doc else "",
                    current_user_id=str(user.id),
                ):
                    return True, t.to_state_link.state.slug, None
                return False, None, f"You do not have permission to perform '{action}'. Required roles: {', '.join(roles)}"
        return False, None, f"Action '{action}' not available from state '{current_state}'"

    async def build_workflow_meta_dict(self, entity: str, json_workflow_meta: Any = None) -> Optional[dict]:
        """Build the workflow metadata dict for an entity.
        Falls back to JSON workflow config when no DB workflow exists.
        Pass show_actions=False in the JSON workflow config to display a read-only
        state badge instead of action buttons (e.g. for line entities whose state
        is managed by a parent entity, not manually by the user).
        """
        import re

        def _slugify(s: str) -> str:
            return re.sub(r'\s+', '_', s.strip().lower())

        def _state_to_dict(state: Any, index: int) -> dict[str, Any]:
            if isinstance(state, dict):
                label = state.get("label") or state.get("name") or state.get("slug") or f"state_{index + 1}"
                slug_source = state.get("slug") or state.get("name") or label
                return {
                    "slug": _slugify(str(slug_source)),
                    "label": label,
                    "color": state.get("color"),
                    "is_initial": bool(state.get("is_initial", index == 0)),
                }

            label = str(state)
            return {
                "slug": _slugify(label),
                "label": label,
                "color": None,
                "is_initial": index == 0,
            }

        def _transition_to_dict(transition: Any) -> dict[str, Any]:
            if isinstance(transition, dict):
                from_state = transition.get("from") or transition.get("from_state") or ""
                action = transition.get("action") or ""
                to_state = transition.get("to") or transition.get("to_state") or ""
                return {
                    "from_state": _slugify(str(from_state)),
                    "action": _slugify(str(action)),
                    "action_label": transition.get("label") or str(action),
                    "to_state": _slugify(str(to_state)),
                }

            return {
                "from_state": "",
                "action": "",
                "action_label": "",
                "to_state": "",
            }

        # show_actions from JSON meta (default True — show buttons)
        show_actions = getattr(json_workflow_meta, 'show_actions', True) if json_workflow_meta else True

        workflow = await self.get_workflow(entity)

        if workflow and workflow.is_active:
            initial_link = next((sl for sl in workflow.state_links if sl.is_initial), None)
            return {
                "enabled": True,
                "show_actions": show_actions,
                "initial_state": initial_link.state.slug if initial_link else None,
                "default_state": initial_link.state.slug if initial_link else None,
                "states": [
                    {"slug": sl.state.slug, "label": sl.state.label, "color": sl.state.color, "is_initial": sl.is_initial}
                    for sl in sorted(workflow.state_links, key=lambda x: x.sort_order)
                ],
                "transitions": [
                    {
                        "from_state": t.from_state_link.state.slug,
                        "action": t.action_ref.slug,
                        "action_label": t.action_ref.label,
                        "to_state": t.to_state_link.state.slug,
                    }
                    for t in sorted(self._get_workflow_transitions(workflow), key=lambda x: x.sort_order)
                ],
            }
        elif json_workflow_meta and getattr(json_workflow_meta, 'enabled', False):
            return {
                "enabled": True,
                "show_actions": show_actions,
                "initial_state": _slugify(json_workflow_meta.initial_state) if json_workflow_meta.initial_state else "draft",
                "default_state": _slugify(json_workflow_meta.initial_state) if json_workflow_meta.initial_state else "draft",
                "states": [
                    _state_to_dict(s, i)
                    for i, s in enumerate(json_workflow_meta.states)
                ],
                "transitions": [
                    _transition_to_dict(t)
                    for t in json_workflow_meta.transitions
                ],
            }

        return None
