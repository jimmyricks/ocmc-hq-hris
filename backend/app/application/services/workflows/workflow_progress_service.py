"""
Workflow Progress Service
=========================

Builds a generic workflow progress view for any entity with a workflow.

In the barebones backend, the EAM-specific child-node builders have been
removed. The service still returns:
  - current state
  - available next actions
  - workflow steps

Future business modules can add child-node builders by overriding the
entity-specific branches in _build_node.
"""
from typing import Any, Optional

from app.meta.registry import MetaRegistry


class WorkflowProgressService:
    def __init__(self, workflow_repo, entity_repo):
        self.workflow_repo = workflow_repo
        self.entity_repo = entity_repo

    async def get_progress(
        self, entity: str, record_id: str, user: Any = None
    ) -> dict[str, Any]:
        record = await self.entity_repo.get_by_id(entity, record_id)
        if not record:
            raise ValueError(f"Record '{record_id}' not found for entity '{entity}'")

        node = await self._build_node(entity, record, user)
        return {
            "entity": entity,
            "record_id": record_id,
            "title": node.get("title"),
            "summary": node.get("summary"),
            "node": node,
        }

    async def _build_node(self, entity: str, record: Any, user: Any = None) -> dict[str, Any]:
        record_id = getattr(record, "id", None)
        workflow = await self.workflow_repo.get_workflow(
            entity, workspace_id=getattr(record, "workspace_id", None)
        )
        workflow_def = self._workflow_definition(workflow, entity)
        title = self._get_record_title(entity, record)
        current_state = self._normalize_state(
            self._record_state(entity, record) or workflow_def.get("initial_state")
        )
        if workflow:
            current_state = self.workflow_repo.resolve_state_slug(
                workflow, current_state
            )
        allowed_actions = await self.workflow_repo.get_available_actions(
            entity,
            current_state,
            user,
            record_id,
            workflow=workflow,
            doc=record,
        )
        allowed_by_slug = {item["action_slug"]: item for item in allowed_actions}
        transitions_from_current = [
            t
            for t in workflow_def["transitions"]
            if t["from_state"] == current_state and t["action"] in allowed_by_slug
        ]
        next_actions = [
            {
                "action_slug": t["action"],
                "action_label": t["action_label"],
                "from_state": t["from_state"],
                "to_state": t["to_state"],
                "to_state_label": self._state_label(workflow_def, t["to_state"]),
                "allowed_roles": t.get("allowed_roles", []),
                "action": t["action"],
                "label": t["action_label"],
                "target_state": t["to_state"],
                "target_label": self._state_label(workflow_def, t["to_state"]),
                "description": self._transition_description(entity, t["action"], t["to_state"]),
            }
            for t in transitions_from_current
        ]

        return {
            "entity": entity,
            "record_id": record_id,
            "label": MetaRegistry.get(entity).label if MetaRegistry.get(entity) else entity.replace("_", " ").title(),
            "title": title,
            "current_state": current_state,
            "current_state_label": self._state_label(workflow_def, current_state),
            "next_actions": next_actions,
            "steps": self._build_steps(entity, workflow_def, current_state),
            "summary": None,
            "children": [],
        }

    def _record_state(self, entity: str, record: Any) -> Optional[str]:
        meta = MetaRegistry.get(entity)
        configured = getattr(getattr(meta, "workflow", None), "state_field", None)
        for field_name in (configured, "workflow_state", "status"):
            if field_name and hasattr(record, field_name):
                value = getattr(record, field_name, None)
                if value is not None:
                    return str(value)
        return None

    def _workflow_definition(self, workflow: Any, entity: str) -> dict[str, Any]:
        if not workflow:
            return {
                "name": entity,
                "initial_state": None,
                "states": [],
                "transitions": [],
            }

        states = []
        for sl in workflow.state_links:
            if sl.state:
                states.append({
                    "id": sl.state.id,
                    "slug": sl.state.slug,
                    "label": sl.state.label,
                    "color": sl.state.color,
                    "is_initial": sl.is_initial,
                    "sort_order": sl.sort_order,
                })

        initial_state = next((s["slug"] for s in states if s["is_initial"]), None)

        transitions = []
        for sl in workflow.state_links:
            for t in sl.outgoing_transitions:
                if t.action_ref and t.to_state_link and t.to_state_link.state:
                    transitions.append({
                        "action": t.action_ref.slug,
                        "action_label": t.action_ref.label,
                        "from_state": sl.state.slug if sl.state else None,
                        "to_state": t.to_state_link.state.slug,
                        "allowed_roles": t.get_allowed_roles(),
                    })

        return {
            "name": workflow.name,
            "initial_state": initial_state,
            "states": states,
            "transitions": transitions,
        }

    def _get_record_title(self, entity: str, record: Any) -> str:
        meta = MetaRegistry.get(entity)
        title_field = meta.title_field if meta else "id"
        title = getattr(record, title_field, None)
        if title is not None and str(title).strip():
            return str(title)
        record_id = getattr(record, "id", None)
        return str(record_id) if record_id else ""

    def _normalize_state(self, state: Optional[str]) -> str:
        import re
        if not state:
            return ""
        slug = state.lower().strip()
        slug = re.sub(r"[^a-z0-9\s_]", "", slug)
        slug = re.sub(r"\s+", "_", slug)
        return slug.strip("_")

    def _state_label(self, workflow_def: dict, slug: str) -> str:
        for s in workflow_def["states"]:
            if s["slug"] == slug:
                return s["label"]
        return slug.replace("_", " ").title()

    def _build_steps(self, entity: str, workflow_def: dict, current_state: str) -> list[dict]:
        steps = []
        for s in workflow_def["states"]:
            steps.append({
                "slug": s["slug"],
                "label": s["label"],
                "is_initial": s["is_initial"],
                "is_current": s["slug"] == current_state,
                "color": s.get("color"),
            })
        return steps

    def _transition_description(self, entity: str, action: str, to_state: str) -> str:
        """Return a generic description for a workflow transition."""
        return f"Perform '{action}' to move to '{self._normalize_state(to_state).replace('_', ' ').title()}'."
