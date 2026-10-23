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

    def _workflow_options(self):
        return (
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

    async def get_workflow(
        self, entity: str, workspace_id: Optional[str] = None
    ) -> Optional[Workflow]:
        """Return the active workflow for a scope, preferring its explicit default."""
        if workspace_id:
            result = await self.db.execute(
                select(Workflow)
                .where(
                    Workflow.target_entity == entity,
                    Workflow.workspace_id == workspace_id,
                    Workflow.is_active == True,
                )
                .options(*self._workflow_options())
                .order_by(
                    Workflow.is_default.desc(),
                    Workflow.updated_at.desc(),
                    Workflow.created_at.asc(),
                )
            )
            workflow = result.scalars().first()
            if workflow:
                return workflow

        result = await self.db.execute(
            select(Workflow)
            .where(
                Workflow.target_entity == entity,
                Workflow.workspace_id.is_(None),
                Workflow.is_active == True,
            )
            .options(*self._workflow_options())
            .order_by(Workflow.created_at.asc())
        )
        return result.scalars().first()

    async def get_initial_state(
        self, entity: str, workspace_id: Optional[str] = None
    ) -> Optional[str]:
        workflow = await self.get_workflow(entity, workspace_id=workspace_id)
        if not workflow:
            return None
        initial_link = next((sl for sl in workflow.state_links if sl.is_initial), None)
        return initial_link.state.slug if initial_link else None

    def resolve_state_slug(self, workflow: Workflow, current_state: str) -> str:
        """Resolve a persisted or legacy status to a linked workflow state."""
        return self._resolve_state_slug(workflow, current_state)

    def _resolve_state_slug(self, workflow: Workflow, current_state: str) -> str:
        """Map legacy task statuses onto workspace workflow slugs when needed."""
        if not current_state:
            return current_state
        linked_states = {
            link.state.slug for link in workflow.state_links if link.state
        }
        if current_state in linked_states:
            return current_state
        legacy_aliases = {
            "draft_assigned": "draft",
            "in_progress": "pending",
            "for_review": "for_approval",
            "closed": "done",
        }
        alias = legacy_aliases.get(current_state)
        return alias if alias in linked_states else current_state

    async def _get_doc(self, entity: str, record_id: str | None, doc: Any = None) -> Any:
        if doc is not None or not record_id:
            return doc
        from app.infrastructure.database.repositories.entity_repository import get_entity_model

        model = get_entity_model(entity)
        if not model:
            return None
        result = await self.db.execute(select(model).where(model.id == record_id))
        return result.scalar_one_or_none()

    async def _get_effective_roles(self, user: Any, doc: Any = None) -> set[str]:
        """Combine global RBAC roles with the user's role in the record workspace."""
        roles = set(getattr(user, "roles", []) or []) if user else set()
        workspace_id = getattr(doc, "workspace_id", None) if doc else None
        if not workspace_id or not user:
            return roles

        from app.modules.workspaces.models import WorkspaceMembership

        membership_role = await self.db.scalar(
            select(WorkspaceMembership.membership_role).where(
                WorkspaceMembership.workspace_id == workspace_id,
                WorkspaceMembership.user_id == user.id,
                WorkspaceMembership.membership_role == "supervisor",
                WorkspaceMembership.is_active == True,
            )
        )
        if membership_role:
            roles.add(membership_role)
            roles.add(f"workspace:{membership_role}")

        project_id = getattr(doc, "project_id", None)
        if project_id:
            from app.modules.project_tasks.models import Project, ProjectMember

            project = await self.db.get(Project, project_id)
            project_member_role = await self.db.scalar(
                select(ProjectMember.role).where(
                    ProjectMember.project_id == project_id,
                    ProjectMember.user_id == user.id,
                    ProjectMember.is_active.is_(True),
                )
            )
            if project_member_role or (project and project.manager_id == user.id):
                role = project_member_role or "manager"
                roles.add(f"project:{role}")
                if role == "manager":
                    roles.add("workspace:supervisor")
                else:
                    roles.add("workspace:member")
        return roles

    async def get_available_actions(
        self,
        entity: str,
        current_state: str,
        user: Any = None,
        record_id: str = None,
        workspace_id: Optional[str] = None,
        workflow: Optional[Workflow] = None,
        doc: Any = None,
    ) -> list[dict[str, Any]]:
        doc = await self._get_doc(entity, record_id, doc)
        if not workspace_id:
            workspace_id = getattr(doc, "workspace_id", None)
        if workflow is None:
            workflow = await self.get_workflow(entity, workspace_id=workspace_id)
        if not workflow:
            return []

        user_roles = await self._get_effective_roles(user, doc)
        is_super = bool(
            user
            and (
                getattr(user, "is_superuser", False)
                or "SystemManager" in user_roles
                or "Administrator" in user_roles
            )
        )

        current_state = self._resolve_state_slug(workflow, current_state)
        available = []
        for transition in self._get_workflow_transitions(workflow):
            if (
                not transition.action_ref
                or transition.from_state_link.state.slug != current_state
            ):
                continue
            roles = transition.get_allowed_roles()
            if is_super or can_act_on_transition(
                roles,
                list(user_roles),
                created_by=str(doc.created_by) if doc else "",
                current_user_id=str(user.id) if user else "",
            ):
                available.append(
                    {
                        "action_slug": transition.action_ref.slug,
                        "action_label": transition.action_ref.label,
                        "to_state_slug": transition.to_state_link.state.slug,
                        "to_state_label": transition.to_state_link.state.label,
                    }
                )
        return available

    async def find_transition(
        self,
        entity: str,
        current_state: str,
        action: str,
        user: Any = None,
        record_id: str = None,
        workspace_id: Optional[str] = None,
        workflow: Optional[Workflow] = None,
        doc: Any = None,
    ) -> Tuple[Optional[WorkflowTransition], Optional[str]]:
        doc = await self._get_doc(entity, record_id, doc)
        if not workspace_id:
            workspace_id = getattr(doc, "workspace_id", None)
        if workflow is None:
            workflow = await self.get_workflow(entity, workspace_id=workspace_id)
        if not workflow:
            return None, f"No workflow found for entity '{entity}'"

        user_roles = await self._get_effective_roles(user, doc)
        is_super = bool(
            user
            and (
                getattr(user, "is_superuser", False)
                or "SystemManager" in user_roles
                or "Administrator" in user_roles
            )
        )

        current_state = self._resolve_state_slug(workflow, current_state)
        for transition in self._get_workflow_transitions(workflow):
            if (
                not transition.action_ref
                or transition.from_state_link.state.slug != current_state
                or transition.action_ref.slug != action
            ):
                continue
            roles = transition.get_allowed_roles()
            if is_super or can_act_on_transition(
                roles,
                list(user_roles),
                created_by=str(doc.created_by) if doc else "",
                current_user_id=str(user.id) if user else "",
            ):
                return transition, None
            return (
                None,
                "You do not have permission to perform "
                f"'{action}'. Required roles: {', '.join(roles)}",
            )
        return None, f"Action '{action}' not available from state '{current_state}'"

    async def validate_transition(
        self,
        entity: str,
        current_state: str,
        action: str,
        user: Any = None,
        record_id: str = None,
        workspace_id: Optional[str] = None,
        workflow: Optional[Workflow] = None,
        doc: Any = None,
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        transition, error = await self.find_transition(
            entity,
            current_state,
            action,
            user,
            record_id,
            workspace_id=workspace_id,
            workflow=workflow,
            doc=doc,
        )
        if not transition:
            return False, None, error
        return True, transition.to_state_link.state.slug, None

    async def build_workflow_meta_dict(
        self,
        entity: str,
        json_workflow_meta: Any = None,
        workspace_id: Optional[str] = None,
    ) -> Optional[dict]:
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

        workflow = await self.get_workflow(entity, workspace_id=workspace_id)

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
