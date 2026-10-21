"""Row scope enforcement service.

Applies `row_scope` filters to SQLAlchemy queries and single-record access checks.
The service is used by list, detail, options, tree, and child endpoints.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import and_, or_, select

from app.core.constants.permissions import (
    ROW_SCOPE_ALL,
    ROW_SCOPE_OWNER_ONLY,
    ROW_SCOPE_OWNER_OR_ASSIGNED,
    RESERVED_ROLE_OWNER,
)
from app.core.exceptions import BadRequestError, ForbiddenError, NotFoundError
from app.application.services.access_control.rbac_service import (
    is_system_admin_entity,
)


class RowScopeConfigError(ValueError):
    """Raised when the configured owner field cannot be resolved on the model."""


class RowScopeService:
    """Apply row-scope filters to queries and single-record access checks."""

    def __init__(
        self,
        db,
        rbac_service,
        meta_registry,
        workflow_repo,
        requested_workspace_id: str | None = None,
    ):
        self.db = db
        self.rbac = rbac_service
        self.meta_registry = meta_registry
        self.workflow_repo = workflow_repo
        self.requested_workspace_id = requested_workspace_id

    async def apply_scope_to_query(
        self,
        query,
        model,
        entity: str,
        user_id: str,
        role_ids: list[str],
        role_names: list[str],
        is_superuser: bool,
    ):
        """Add row-scope WHERE clauses to a query."""
        if entity == "user_task_rate":
            return query.where(False)
        if is_system_admin_entity(entity) and not self._is_system_admin(
            role_names, is_superuser
        ):
            return query.where(False)
        workspace_entity = self._is_workspace_entity(entity, model)
        query = await self._apply_workspace_scope(
            query, model, entity, user_id, role_names, is_superuser
        )
        if is_superuser or workspace_entity:
            return query

        scopes = await self.rbac.get_row_scope(role_ids, entity)
        if ROW_SCOPE_ALL in scopes:
            return query

        owner_field = self.meta_registry.get_owner_field(entity)
        owner_col = getattr(model, owner_field, None)
        if owner_col is None and (
            ROW_SCOPE_OWNER_ONLY in scopes or ROW_SCOPE_OWNER_OR_ASSIGNED in scopes
        ):
            raise RowScopeConfigError(
                f"Entity '{entity}' row scope uses owner field '{owner_field}' "
                f"but that column is not present on the model."
            )

        owner_condition = owner_col == user_id if owner_col is not None else None

        conditions = []
        if owner_condition is not None and ROW_SCOPE_OWNER_ONLY in scopes:
            conditions.append(owner_condition)

        if ROW_SCOPE_OWNER_OR_ASSIGNED in scopes:
            if owner_condition is not None:
                conditions.append(owner_condition)
            allowed_states = await self._get_allowed_states_for_user(entity, role_names)
            if allowed_states and hasattr(model, "workflow_state"):
                conditions.append(getattr(model, "workflow_state").in_(allowed_states))

        if not conditions:
            return query
        return query.where(or_(*conditions))

    async def can_access_record(
        self,
        record,
        entity: str,
        user_id: str,
        role_ids: list[str],
        role_names: list[str],
        is_superuser: bool,
    ) -> bool:
        """Check if a single record is visible to the user under row scope."""
        if entity == "user_task_rate":
            return False
        if is_system_admin_entity(entity) and not self._is_system_admin(
            role_names, is_superuser
        ):
            return False
        workspace_entity = self._is_workspace_entity(entity, record.__class__)
        if workspace_entity:
            model = record.__class__
            scoped = await self._apply_workspace_scope(
                select(model.id),
                model,
                entity,
                user_id,
                role_names,
                is_superuser,
            )
            result = await self.db.execute(scoped.where(model.id == record.id))
            if result.scalar_one_or_none() is None:
                return False
            return True
        elif is_superuser:
            return True

        if is_superuser:
            return True

        scopes = await self.rbac.get_row_scope(role_ids, entity)
        if ROW_SCOPE_ALL in scopes:
            return True

        owner_field = self.meta_registry.get_owner_field(entity)
        owner_value = getattr(record, owner_field, None)

        if owner_value == user_id:
            return True

        if ROW_SCOPE_OWNER_OR_ASSIGNED in scopes:
            allowed_states = await self._get_allowed_states_for_user(entity, role_names)
            if allowed_states and hasattr(record, "workflow_state"):
                return getattr(record, "workflow_state") in allowed_states

        return False

    @staticmethod
    def _is_workspace_entity(entity: str, model: Any) -> bool:
        return entity in {
            "workspace",
            "workspace_membership",
            "workspace_team",
            "workspace_resource",
            "project",
            "project_member",
            "task",
            "task_assignment",
            "task_submission",
            "task_approval",
            "task_link",
            "task_type",
            "planner_event",
            "schedule_series",
            "schedule_occurrence",
            "resource_booking",
            "workspace_team",
        } or hasattr(model, "workspace_id")

    async def can_read_entity(
        self,
        entity: str,
        user_id: str,
        role_names: list[str],
        is_superuser: bool,
    ) -> bool:
        if entity == "user_task_rate":
            return False
        if is_system_admin_entity(entity):
            return self._is_system_admin(role_names, is_superuser)
        if entity == "workspace_membership":
            return False
        if not self._is_workspace_entity(entity, object()):
            return False
        from app.modules.workspaces.services import WorkspaceService

        if WorkspaceService.is_hr(role_names) and not WorkspaceService.is_system_admin(
            role_names, is_superuser
        ):
            return False

        try:
            await WorkspaceService.resolve_context(
                self.db,
                user_id,
                role_names,
                is_superuser,
                self.requested_workspace_id,
            )
            return True
        except (BadRequestError, ForbiddenError, NotFoundError):
            return False

    @staticmethod
    def _is_system_admin(role_names: list[str], is_superuser: bool) -> bool:
        from app.modules.workspaces.services import WorkspaceService

        return WorkspaceService.is_system_admin(role_names, is_superuser)

    async def _apply_workspace_scope(
        self,
        query,
        model: Any,
        entity: str,
        user_id: str,
        role_names: list[str],
        is_superuser: bool,
    ):
        if not self._is_workspace_entity(entity, model):
            return query

        from app.modules.project_tasks.models import (
            Project,
            ProjectMember,
            Task,
            TaskApproval,
            TaskAssignment,
            TaskLink,
            TaskSubmission,
        )
        from app.modules.workspaces.models import (
            ScheduleOccurrence,
            ScheduleSeries,
            Workspace,
            WorkspaceMembership,
        )
        from app.modules.workspaces.services import WorkspaceService

        context = await WorkspaceService.resolve_context(
            self.db,
            user_id,
            role_names,
            is_superuser,
            self.requested_workspace_id,
        )
        if context.is_global:
            return query
        if not context.workspace_ids:
            return query.where(False)

        workspace_ids = context.workspace_ids
        is_admin = WorkspaceService.is_admin(role_names, is_superuser)
        project_member_ids = select(ProjectMember.project_id).where(
            ProjectMember.user_id == user_id,
            ProjectMember.is_active.is_(True),
        )
        active_task_ids = (
            select(TaskAssignment.task_id)
            .join(Task, Task.id == TaskAssignment.task_id)
            .where(
                TaskAssignment.user_id == user_id,
                TaskAssignment.is_active.is_(True),
                Task.workspace_id.is_not(None),
            )
        )
        assigned_project_ids = select(Task.project_id).where(
            Task.id.in_(active_task_ids)
        )
        supervisor = (
            not is_admin
            and await self._workspace_role(
                context.active_workspace_id, user_id, role_names, is_superuser
            )
            == "supervisor"
        )
        project_condition = (
            Project.workspace_id.in_(workspace_ids)
            if is_admin or supervisor
            else and_(
                Project.workspace_id.is_not(None),
                or_(
                    Project.id.in_(project_member_ids),
                    Project.id.in_(assigned_project_ids),
                ),
            )
        )
        visible_projects = select(Project.id).where(project_condition)

        if entity == "workspace":
            return query.where(Workspace.id.in_(workspace_ids))
        if entity == "workspace_membership":
            return query.where(
                WorkspaceMembership.workspace_id.in_(workspace_ids),
                WorkspaceMembership.user_id == user_id,
            )
        if entity == "project":
            return query.where(project_condition)
        if entity == "project_member":
            condition = ProjectMember.project_id.in_(visible_projects)
            if not (is_admin or supervisor):
                condition = ProjectMember.user_id == user_id
            return query.where(condition)
        if entity == "task":
            if is_admin or supervisor:
                return query.where(
                    Task.workspace_id.in_(workspace_ids),
                    Task.project_id.in_(visible_projects),
                )
            return query.where(Task.id.in_(active_task_ids))

        task_ids = (
            select(Task.id).where(Task.workspace_id.in_(workspace_ids))
            if is_admin or supervisor
            else active_task_ids
        )
        if entity == "task_assignment":
            condition = TaskAssignment.task_id.in_(task_ids)
            if not (is_admin or supervisor):
                condition = and_(condition, TaskAssignment.user_id == user_id)
            return query.where(condition)
        if entity == "task_submission":
            assignment_ids = select(TaskAssignment.id).where(
                TaskAssignment.task_id.in_(task_ids)
            )
            if not (is_admin or supervisor):
                assignment_ids = select(TaskAssignment.id).where(
                    TaskAssignment.user_id == user_id
                )
            return query.where(TaskSubmission.task_assignment_id.in_(assignment_ids))
        if entity == "task_approval":
            assignment_ids = select(TaskAssignment.id).where(
                TaskAssignment.task_id.in_(task_ids)
            )
            if not (is_admin or supervisor):
                assignment_ids = select(TaskAssignment.id).where(
                    TaskAssignment.user_id == user_id
                )
            submission_ids = select(TaskSubmission.id).where(
                TaskSubmission.task_assignment_id.in_(assignment_ids)
            )
            return query.where(TaskApproval.task_submission_id.in_(submission_ids))
        if entity == "task_link":
            return query.where(TaskLink.task_id.in_(task_ids))
        if entity == "schedule_occurrence":
            series_ids = select(ScheduleSeries.id).where(
                ScheduleSeries.workspace_id.in_(workspace_ids)
            )
            if not is_admin:
                series_ids = select(ScheduleSeries.id).where(
                    or_(
                        ScheduleSeries.workspace_id.in_(workspace_ids),
                        ScheduleSeries.project_id.in_(visible_projects),
                    )
                )
            return query.where(ScheduleOccurrence.series_id.in_(series_ids))

        workspace_column = getattr(model, "workspace_id", None)
        if workspace_column is not None:
            condition = workspace_column.in_(workspace_ids)
            if entity in {"planner_event", "schedule_series"} and not is_admin:
                project_column = getattr(model, "project_id", None)
                if project_column is not None:
                    condition = or_(condition, project_column.in_(visible_projects))
            return query.where(condition)
        return query.where(False)

    async def _workspace_role(
        self,
        workspace_id: str,
        user_id: str,
        role_names: list[str],
        is_superuser: bool,
    ) -> str | None:
        from app.modules.workspaces.models import WorkspaceMembership
        from app.modules.workspaces.services import WorkspaceService

        if WorkspaceService.is_admin(role_names, is_superuser):
            return "administrator"
        return await self.db.scalar(
            select(WorkspaceMembership.membership_role).where(
                WorkspaceMembership.workspace_id == workspace_id,
                WorkspaceMembership.user_id == user_id,
                WorkspaceMembership.is_active.is_(True),
            )
        )

    async def _validate_workspace_links(
        self,
        entity: str,
        workspace_id: str,
        data: dict[str, Any],
        record: Any = None,
    ) -> None:
        from app.modules.project_tasks.models import Project
        from app.modules.workspaces.models import (
            PlannerEvent,
            ScheduleOccurrence,
            ScheduleSeries,
            WorkspaceResource,
            WorkspaceTeam,
        )

        def value(name: str) -> Any:
            if name in data:
                return data[name]
            return getattr(record, name, None) if record is not None else None

        team_id = value("team_id")
        if team_id:
            team = await self.db.get(WorkspaceTeam, team_id)
            if not team or team.workspace_id != workspace_id:
                raise BadRequestError("Team must belong to the selected workspace")

        project_id = value("project_id")
        if project_id:
            project = await self.db.get(Project, project_id)
            if not project or project.workspace_id != workspace_id:
                raise BadRequestError("Project must belong to the selected workspace")

        if entity == "resource_booking":
            resource = await self.db.get(WorkspaceResource, value("resource_id"))
            if not resource or resource.workspace_id != workspace_id:
                raise BadRequestError("Resource must belong to the selected workspace")

            event_id = value("event_id")
            if event_id:
                event = await self.db.get(PlannerEvent, event_id)
                if not event or event.workspace_id != workspace_id:
                    raise BadRequestError("Event must belong to the selected workspace")

            occurrence_id = value("occurrence_id")
            if occurrence_id:
                occurrence = await self.db.get(ScheduleOccurrence, occurrence_id)
                series = (
                    await self.db.get(ScheduleSeries, occurrence.series_id)
                    if occurrence
                    else None
                )
                if not series or series.workspace_id != workspace_id:
                    raise BadRequestError(
                        "Schedule occurrence must belong to the selected workspace"
                    )

    async def prepare_create_data(
        self,
        entity: str,
        data: dict[str, Any],
        user: Any,
    ) -> dict[str, Any]:
        """Assign and validate workspace ownership for tenant-owned generic creates."""
        if entity == "user_task_rate":
            raise ForbiddenError(
                "Employee rates must be managed through the payroll rates API"
            )
        if entity == "payroll_line_item":
            raise ForbiddenError("Payroll line items are managed by payroll generation")
        tenant_root_entities = {
            "project",
            "task_type",
            "planner_event",
            "schedule_series",
            "workspace_resource",
            "workspace_team",
            "resource_booking",
        }
        if entity in {"task_assignment", "task_submission", "task_approval"}:
            raise ForbiddenError("Use the task workflow endpoint for this record")
        if entity not in tenant_root_entities | {"task", "project_member", "task_link"}:
            return data

        from app.core.framework.models.auth import User
        from app.modules.project_tasks.models import Project, ProjectMember, TaskType
        from app.modules.workspaces.models import Workspace, WorkspaceMembership
        from app.modules.workspaces.services import WorkspaceService

        context = await WorkspaceService.resolve_context(
            self.db,
            user.id,
            user.roles,
            user.is_superuser,
            self.requested_workspace_id,
        )
        is_admin = WorkspaceService.is_admin(user.roles, user.is_superuser)
        if entity in tenant_root_entities:
            target_workspace_id = data.get("workspace_id") or context.active_workspace_id
            if not target_workspace_id:
                raise BadRequestError("Select a workspace before creating this record")
            workspace = await self.db.get(Workspace, target_workspace_id)
            if not workspace or not workspace.is_active:
                raise NotFoundError("Workspace", target_workspace_id)
            if not is_admin and target_workspace_id not in context.workspace_ids:
                raise ForbiddenError("You cannot create records in this workspace")
            if not is_admin and await self._workspace_role(
                target_workspace_id, user.id, user.roles, user.is_superuser
            ) != "supervisor":
                raise ForbiddenError("Only workspace supervisors can create this record")
            data["workspace_id"] = target_workspace_id
            if entity == "project" and data.get("is_continuous") is None:
                data["is_continuous"] = False
            await self._validate_workspace_links(entity, target_workspace_id, data)
            if entity == "project" and data.get("is_continuous"):
                data["end_date"] = None
            manager_id = data.get("manager_id")
            if manager_id and not await self.db.scalar(
                select(WorkspaceMembership.id)
                .join(User, User.id == WorkspaceMembership.user_id)
                .where(
                    WorkspaceMembership.workspace_id == target_workspace_id,
                    WorkspaceMembership.user_id == manager_id,
                    WorkspaceMembership.is_active.is_(True),
                    User.is_active.is_(True),
                )
            ):
                raise BadRequestError(
                    "Project manager must be an active member of the workspace"
                )
            return data

        if entity == "task":
            project = await self.db.get(Project, data.get("project_id"))
            if not project:
                raise NotFoundError("Project", data.get("project_id"))
            if not project.workspace_id:
                raise BadRequestError("Map the project to a workspace before adding tasks")
            if not is_admin and (
                project.workspace_id != context.active_workspace_id
                or await self._workspace_role(
                    project.workspace_id, user.id, user.roles, user.is_superuser
                )
                != "supervisor"
            ):
                raise ForbiddenError(
                    "Only supervisors in the project's workspace can create tasks"
                )
            task_type = await self.db.get(TaskType, data.get("task_type_id"))
            if not task_type or task_type.workspace_id != project.workspace_id:
                raise BadRequestError("Task type must belong to the project's workspace")
            if data.get("workspace_id") not in (None, project.workspace_id):
                raise BadRequestError("Task workspace is derived from its project")
            data["workspace_id"] = project.workspace_id
            return data

        if entity == "project_member":
            project = await self.db.get(Project, data.get("project_id"))
            if not project:
                raise NotFoundError("Project", data.get("project_id"))
            member = await self.db.get(User, data.get("user_id"))
            if not member or not member.is_active:
                raise NotFoundError("Active user", data.get("user_id"))
            if not project.workspace_id or not await self.db.scalar(
                select(WorkspaceMembership.id).where(
                    WorkspaceMembership.workspace_id == project.workspace_id,
                    WorkspaceMembership.user_id == member.id,
                    WorkspaceMembership.is_active.is_(True),
                )
            ):
                raise BadRequestError(
                    "Project members must have an active workspace membership"
                )
            if not is_admin and (
                project.workspace_id != context.active_workspace_id
                or await self._workspace_role(
                    project.workspace_id, user.id, user.roles, user.is_superuser
                )
                != "supervisor"
            ):
                raise ForbiddenError(
                    "Only workspace supervisors can manage project membership"
                )
            existing = await self.db.scalar(
                select(ProjectMember.id).where(
                    ProjectMember.project_id == project.id,
                    ProjectMember.user_id == member.id,
                    ProjectMember.is_active.is_(True),
                )
            )
            if existing:
                raise BadRequestError("User is already an active project member")
        if entity == "task_link":
            from app.modules.project_tasks.models import Task

            task = await self.db.get(Task, data.get("task_id"))
            if not task:
                raise NotFoundError("Task", data.get("task_id"))
            project = await self.db.get(Project, task.project_id)
            if not project:
                raise NotFoundError("Project", task.project_id)
            if not is_admin:
                membership = await self.db.scalar(
                    select(ProjectMember.id).where(
                        ProjectMember.project_id == project.id,
                        ProjectMember.user_id == user.id,
                        ProjectMember.is_active.is_(True),
                    )
                )
                if (
                    project.workspace_id not in context.workspace_ids
                    and not membership
                ):
                    raise ForbiddenError("You cannot add links to this task")
                if not project.workspace_id or (
                    project.workspace_id != context.active_workspace_id and not membership
                ):
                    raise ForbiddenError("You cannot add links to this task")
        return data

    async def authorize_record_write(
        self,
        entity: str,
        record: Any,
        data: dict[str, Any],
        user: Any,
    ) -> None:
        if entity == "user_task_rate":
            raise ForbiddenError(
                "Employee rates must be managed through the payroll rates API"
            )
        if not self._is_workspace_entity(entity, record.__class__):
            return
        if entity in {"task_assignment", "task_submission", "task_approval"}:
            raise ForbiddenError("Use the task workflow endpoint for this record")
        if entity == "payroll_line_item":
            raise ForbiddenError("Payroll line items are managed by payroll generation")

        from app.core.framework.models.auth import User
        from app.modules.project_tasks.models import (
            Project,
            ProjectMember,
            Task,
            TaskLink,
            TaskType,
        )
        from app.modules.workspaces.models import WorkspaceMembership
        from app.modules.workspaces.services import WorkspaceService

        context = await WorkspaceService.resolve_context(
            self.db,
            user.id,
            user.roles,
            user.is_superuser,
            self.requested_workspace_id,
        )
        is_admin = WorkspaceService.is_system_admin(user.roles, user.is_superuser)
        workspace_id = getattr(record, "workspace_id", None)
        if entity in {"task", "project_member", "task_link"}:
            if isinstance(record, TaskLink):
                task = await self.db.get(Task, data.get("task_id", record.task_id))
                project = await self.db.get(Project, task.project_id) if task else None
            else:
                project = await self.db.get(
                    Project, data.get("project_id", record.project_id)
                )
            workspace_id = project.workspace_id if project else None
        if entity not in {"task", "project_member", "task_link"}:
            requested_workspace = data.get("workspace_id", workspace_id)
            if requested_workspace != workspace_id:
                raise ForbiddenError("Workspace ownership cannot be changed directly")
        if entity in {
            "project",
            "task_type",
            "planner_event",
            "schedule_series",
            "workspace_resource",
            "workspace_team",
            "resource_booking",
        }:
            if not workspace_id:
                raise ForbiddenError("Unmapped records must be repaired before editing")
            await self._validate_workspace_links(
                entity, workspace_id, data, record=record
            )

        if entity == "project":
            if "is_continuous" in data and data["is_continuous"] is None:
                raise BadRequestError("Project continuity must be set to true or false")
            if data.get("is_continuous", record.is_continuous):
                data["end_date"] = None
            manager_id = data.get("manager_id", record.manager_id)
            if manager_id and not await self.db.scalar(
                select(WorkspaceMembership.id)
                .join(User, User.id == WorkspaceMembership.user_id)
                .where(
                    WorkspaceMembership.workspace_id == workspace_id,
                    WorkspaceMembership.user_id == manager_id,
                    WorkspaceMembership.is_active.is_(True),
                    User.is_active.is_(True),
                )
            ):
                raise BadRequestError(
                    "Project manager must be an active member of the workspace"
                )
        elif entity == "task":
            project = await self.db.get(Project, data.get("project_id", record.project_id))
            if not project or project.workspace_id != record.workspace_id:
                raise ForbiddenError("Tasks cannot be moved between workspaces")
            if data.get("workspace_id", record.workspace_id) != project.workspace_id:
                raise BadRequestError("Task workspace must match its project")
            task_type_id = data.get("task_type_id", record.task_type_id)
            task_type = await self.db.get(TaskType, task_type_id) if task_type_id else None
            if not task_type or task_type.workspace_id != project.workspace_id:
                raise BadRequestError("Task type must belong to the project's workspace")
        elif entity == "project_member":
            project = await self.db.get(Project, record.project_id)
            member_id = data.get("user_id", record.user_id)
            member = await self.db.get(User, member_id)
            if not project or not member or not member.is_active or not await self.db.scalar(
                select(WorkspaceMembership.id).where(
                    WorkspaceMembership.workspace_id == project.workspace_id,
                    WorkspaceMembership.user_id == member_id,
                    WorkspaceMembership.is_active.is_(True),
                )
            ):
                raise BadRequestError(
                    "Project members must have an active workspace membership"
                )
        elif entity == "task_link":
            project_member = (
                await self.db.scalar(
                    select(ProjectMember.id).where(
                        ProjectMember.project_id == project.id,
                        ProjectMember.user_id == user.id,
                        ProjectMember.is_active.is_(True),
                    )
                )
                if project
                else None
            )
            if not project or (
                not is_admin
                and project.workspace_id != context.active_workspace_id
                and not project_member
            ):
                raise ForbiddenError("You cannot modify links on this task")

        if is_admin:
            return
        if not workspace_id or workspace_id != context.active_workspace_id:
            raise ForbiddenError("Changes are limited to the active workspace")
        if await self._workspace_role(
            workspace_id, user.id, user.roles, user.is_superuser
        ) != "supervisor":
            raise ForbiddenError("Only workspace supervisors can modify this record")

    def authorize_collection_action(self, entity: str, user: Any) -> None:
        if entity == "user_task_rate":
            raise ForbiddenError(
                "Employee rates must be managed through the payroll rates API"
            )
        if not self._is_workspace_entity(entity, object()):
            return
        from app.modules.workspaces.services import WorkspaceService

        if not WorkspaceService.is_system_admin(user.roles, user.is_superuser):
            raise ForbiddenError("Bulk actions are not available for workspace records")

    async def authorize_create_data(
        self, entity: str, data: dict[str, Any], user: Any
    ) -> dict[str, Any]:
        return await self.prepare_create_data(entity, data, user)

    async def _get_allowed_states_for_user(
        self, entity: str, role_names: list[str]
    ) -> set[str]:
        """Return states that have an outgoing transition allowed for any of the user's roles.

        The pseudo-role "Owner" is ignored because the ``created_by = :user_id`` check
        already covers record ownership.
        """
        workflow = await self.workflow_repo.get_workflow(entity)
        if not workflow:
            return set()

        transitions = []
        seen = set()
        for state_link in workflow.state_links:
            for transition in state_link.outgoing_transitions:
                if transition.id not in seen:
                    transitions.append(transition)
                    seen.add(transition.id)

        user_roles = set(role_names)
        owner_aliases = {RESERVED_ROLE_OWNER, "Owner"}
        allowed_states = set()
        for transition in transitions:
            allowed = set(transition.get_allowed_roles())
            # The owner pseudo-role is handled by the `created_by = :user_id` clause,
            # so it should not add states for non-owners.
            allowed -= owner_aliases
            if user_roles.intersection(allowed):
                allowed_states.add(transition.from_state_link.state.slug)
        return allowed_states
