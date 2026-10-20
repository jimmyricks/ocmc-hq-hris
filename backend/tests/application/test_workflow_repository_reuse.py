from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.infrastructure.database.repositories.workflow_repository import (
    WorkflowRepository,
)
from app.api.entries.entity_workflow import _workflow_state_field


@pytest.mark.asyncio
async def test_validate_transition_reuses_loaded_workflow_and_record():
    db = AsyncMock()
    repository = WorkflowRepository(db)
    workflow = SimpleNamespace(state_links=[])
    record = SimpleNamespace(created_by="owner")
    user = SimpleNamespace(id="owner", roles=[])

    result = await repository.validate_transition(
        "task",
        "in_progress",
        "submit",
        user,
        "TASK-1",
        workflow=workflow,
        doc=record,
    )

    assert result == (
        False,
        None,
        "Action 'submit' not available from state 'in_progress'",
    )
    db.execute.assert_not_awaited()


def test_workflow_uses_status_when_model_has_no_workflow_state_column():
    model = type("TaskModel", (), {"status": None})
    meta = SimpleNamespace(
        workflow=SimpleNamespace(state_field="workflow_state")
    )

    assert _workflow_state_field(meta, model) == "status"
