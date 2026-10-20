from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.core.exceptions import BadRequestError, ForbiddenError
from app.application.services.access_control.row_scope_service import RowScopeService
from app.modules.payroll.models import PayrollLineItem
from app.modules.payroll.services import PayrollService
from app.modules.workspaces.services import WorkspaceService


def test_payroll_uses_the_task_type_rate_for_the_project_workspace():
    task_type = SimpleNamespace(workspace_id="workspace-bahandi", unit_rate=125.5)

    assert PayrollService._resolve_rate(task_type, "workspace-bahandi") == 125.5


@pytest.mark.asyncio
async def test_hr_payroll_scope_is_global_without_granting_workspace_admin():
    class RBAC:
        pass

    scope = RowScopeService(
        db=None,
        rbac_service=RBAC(),
        meta_registry=None,
        workflow_repo=None,
    )
    query = await scope.apply_scope_to_query(
        select(PayrollLineItem),
        PayrollLineItem,
        "payroll_line_item",
        user_id="hr-user",
        role_ids=[],
        role_names=["HR"],
        is_superuser=False,
    )

    assert "WHERE" not in str(query)
    assert WorkspaceService.is_payroll_admin(["HR"], False)
    assert not WorkspaceService.is_admin(["HR"], False)


@pytest.mark.asyncio
async def test_payroll_line_items_cannot_be_mutated_through_generic_crud():
    class RBAC:
        pass

    scope = RowScopeService(
        db=None,
        rbac_service=RBAC(),
        meta_registry=None,
        workflow_repo=None,
    )
    user = SimpleNamespace(id="hr-user", roles=["HR"], is_superuser=False)

    with pytest.raises(ForbiddenError, match="managed by payroll generation"):
        await scope.prepare_create_data("payroll_line_item", {}, user)
    with pytest.raises(ForbiddenError, match="managed by payroll generation"):
        await scope.authorize_record_write(
            "payroll_line_item", PayrollLineItem(), {}, user
        )


@pytest.mark.parametrize(
    ("task_type", "workspace_id", "message"),
    [
        (
            SimpleNamespace(workspace_id="workspace-bahandi", unit_rate=125),
            None,
            "Map the project",
        ),
        (
            SimpleNamespace(workspace_id=None, unit_rate=125),
            "workspace-bahandi",
            "Map the task type",
        ),
        (None, "workspace-bahandi", "Map the task type"),
    ],
)
def test_payroll_rejects_unmapped_or_cross_workspace_rates(
    task_type, workspace_id, message
):
    with pytest.raises(BadRequestError, match=message):
        PayrollService._resolve_rate(task_type, workspace_id)
