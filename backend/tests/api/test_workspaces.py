from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.database import Base
from app.core.exceptions import ForbiddenError
from app.core.framework.models.auth import EntityPermission, Role, User
from app.core.security import CurrentUser, get_current_user_from_token
from app.application.services.access_control.rbac_service import RBACAppService
from app.infrastructure.database.repositories.auth_repository import AuthRepository
from app.core.seeds.permissions import seed_entity_permissions
from app.core.seeds.roles import seed_roles
from app.application.services.access_control.row_scope_service import RowScopeService
from app.modules.project_tasks.models import (
    Project,
    ProjectMember,
    Task,
    TaskAssignment,
)
from app.modules.workspaces.models import Workspace, WorkspaceMembership, WorkspaceTeam
from app.modules.workspaces.services import WorkspaceContext, WorkspaceService


@pytest.mark.asyncio
async def test_workspace_defaults_are_seeded_idempotently():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as db:
        await WorkspaceService.seed_defaults(db)
        await WorkspaceService.seed_defaults(db)
        assert await db.scalar(select(func.count()).select_from(Workspace)) == 4
        teams = await db.scalars(
            select(WorkspaceTeam).where(
                WorkspaceTeam.workspace_id == "workspace-bahandi"
            )
        )
        assert {team.slug for team in teams} == {
            "social-media-management",
            "artist-management",
        }

    await engine.dispose()


@pytest.mark.asyncio
async def test_workspace_context_limits_members_and_supervisors():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as db:
        await WorkspaceService.seed_defaults(db)
        member = User(
            id=str(uuid4()),
            username="member",
            email="member@example.test",
            full_name="Member",
            hashed_password="unused",
        )
        supervisor = User(
            id=str(uuid4()),
            username="supervisor",
            email="supervisor@example.test",
            full_name="Supervisor",
            hashed_password="unused",
        )
        db.add_all([member, supervisor])
        await db.flush()
        db.add_all(
            [
                WorkspaceMembership(
                    id=str(uuid4()),
                    workspace_id="workspace-fourth-street",
                    user_id=member.id,
                    membership_role="member",
                    is_home=True,
                    is_active=True,
                ),
                WorkspaceMembership(
                    id=str(uuid4()),
                    workspace_id="workspace-fourth-street",
                    user_id=supervisor.id,
                    membership_role="supervisor",
                    is_home=True,
                    is_active=True,
                ),
                WorkspaceMembership(
                    id=str(uuid4()),
                    workspace_id="workspace-bahandi",
                    user_id=supervisor.id,
                    membership_role="supervisor",
                    is_home=False,
                    is_active=True,
                ),
            ]
        )
        await db.commit()

        with pytest.raises(ForbiddenError, match="not assigned"):
            await WorkspaceService.resolve_context(
                db,
                member.id,
                [],
                False,
                "workspace-bahandi",
            )

        selected = await WorkspaceService.resolve_context(
            db,
            supervisor.id,
            [],
            False,
            "workspace-bahandi",
        )
        assert selected.active_workspace_id == "workspace-bahandi"
        assert selected.workspace_ids == ("workspace-bahandi",)

        with pytest.raises(ForbiddenError, match="not assigned"):
            await WorkspaceService.resolve_context(
                db,
                supervisor.id,
                [],
                False,
                "workspace-one-heart",
            )

        admin_context = await WorkspaceService.resolve_context(
            db, str(uuid4()), ["Administrator"], False
        )
        assert admin_context.is_global is True
        assert (
            await WorkspaceService.resolve_context(
                db, str(uuid4()), ["HR"], False, "workspace-bahandi"
            )
        ) == WorkspaceContext((), None)
        with pytest.raises(ForbiddenError, match="workspace"):
            await WorkspaceService.resolve_context(db, str(uuid4()), [], False)
        with pytest.raises(ForbiddenError, match="all workspaces"):
            await WorkspaceService.resolve_context(
                db, member.id, [], False, "all"
            )

    await engine.dispose()


@pytest.mark.asyncio
async def test_workspace_query_scope_requires_relevant_project_or_active_assignment():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    class RBAC:
        async def get_row_scope(self, role_ids, entity):
            return ["all"]

    class MetaRegistry:
        @staticmethod
        def get_owner_field(entity):
            return "created_by"

    class WorkflowRepository:
        async def get_workflow(self, entity):
            return None

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as db:
        await WorkspaceService.seed_defaults(db)
        member = User(
            id=str(uuid4()),
            username="scoped-member",
            email="scoped-member@example.test",
            full_name="Scoped Member",
            hashed_password="unused",
        )
        db.add(member)
        await db.flush()
        db.add(
            WorkspaceMembership(
                id=str(uuid4()),
                workspace_id="workspace-fourth-street",
                user_id=member.id,
                membership_role="member",
                is_home=True,
                is_active=True,
            )
        )
        home_project = Project(
            id="home-project",
            workspace_id="workspace-fourth-street",
            name="Home project",
        )
        cross_project = Project(
            id="cross-project",
            workspace_id="workspace-bahandi",
            name="Cross-company project",
        )
        unmapped_project = Project(id="unmapped-project", name="Legacy project")
        db.add_all([home_project, cross_project, unmapped_project])
        db.add(
            ProjectMember(
                id="cross-member",
                project_id=cross_project.id,
                user_id=member.id,
                role="member",
                is_active=True,
            )
        )
        db.add_all(
            [
                Task(
                    id="home-task",
                    project_id=home_project.id,
                    workspace_id=home_project.workspace_id,
                    title="Home task",
                ),
                Task(
                    id="cross-task",
                    project_id=cross_project.id,
                    workspace_id=cross_project.workspace_id,
                    title="Cross-company task",
                ),
                Task(
                    id="unmapped-task",
                    project_id=unmapped_project.id,
                    title="Unmapped task",
                ),
            ]
        )
        db.add(
            TaskAssignment(
                id="cross-task-assignment",
                task_id="cross-task",
                user_id=member.id,
                is_active=True,
                status="active",
            )
        )
        await db.commit()

        scope = RowScopeService(db, RBAC(), MetaRegistry(), WorkflowRepository())
        projects_query = await scope.apply_scope_to_query(
            select(Project),
            Project,
            "project",
            member.id,
            [],
            [],
            False,
        )
        projects = (await db.scalars(projects_query)).all()
        assert {project.id for project in projects} == {"cross-project"}

        tasks_query = await scope.apply_scope_to_query(
            select(Task),
            Task,
            "task",
            member.id,
            [],
            [],
            False,
        )
        tasks = (await db.scalars(tasks_query)).all()
        assert {task.id for task in tasks} == {"cross-task"}

        admin_query = await scope.apply_scope_to_query(
            select(Project),
            Project,
            "project",
            str(uuid4()),
            [],
            ["Administrator"],
            False,
        )
        all_projects = (await db.scalars(admin_query)).all()
        assert len(all_projects) == 3

    await engine.dispose()


@pytest.mark.asyncio
async def test_supervisor_scope_stays_in_assigned_workspace_despite_cross_project_links():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    class RBAC:
        async def get_row_scope(self, role_ids, entity):
            return ["all"]

    class MetaRegistry:
        @staticmethod
        def get_owner_field(entity):
            return "created_by"

    class WorkflowRepository:
        async def get_workflow(self, entity):
            return None

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as db:
        await WorkspaceService.seed_defaults(db)
        supervisor_a = User(
            id="supervisor-a",
            username="supervisor-a",
            email="supervisor-a@example.test",
            full_name="Supervisor A",
            hashed_password="unused",
        )
        supervisor_b = User(
            id="supervisor-b",
            username="supervisor-b",
            email="supervisor-b@example.test",
            full_name="Supervisor B",
            hashed_password="unused",
        )
        project_a = Project(
            id="supervisor-project-a",
            workspace_id="workspace-fourth-street",
            name="Project A",
        )
        project_b = Project(
            id="supervisor-project-b",
            workspace_id="workspace-bahandi",
            name="Project B",
        )
        db.add_all([supervisor_a, supervisor_b, project_a, project_b])
        await db.flush()
        db.add_all(
            [
                WorkspaceMembership(
                    id="supervisor-a-home",
                    workspace_id="workspace-fourth-street",
                    user_id=supervisor_a.id,
                    membership_role="supervisor",
                    is_home=True,
                    is_active=True,
                ),
                WorkspaceMembership(
                    id="supervisor-b-home",
                    workspace_id="workspace-bahandi",
                    user_id=supervisor_b.id,
                    membership_role="supervisor",
                    is_home=True,
                    is_active=True,
                ),
                ProjectMember(
                    id="supervisor-a-cross-member",
                    project_id=project_b.id,
                    user_id=supervisor_a.id,
                    role="member",
                    is_active=True,
                ),
                Task(
                    id="supervisor-task-a",
                    project_id=project_a.id,
                    workspace_id=project_a.workspace_id,
                    title="Task A",
                ),
                Task(
                    id="supervisor-task-b",
                    project_id=project_b.id,
                    workspace_id=project_b.workspace_id,
                    title="Task B",
                ),
                TaskAssignment(
                    id="supervisor-a-cross-assignment",
                    task_id="supervisor-task-b",
                    user_id=supervisor_a.id,
                    is_active=True,
                    status="active",
                ),
            ]
        )
        await db.commit()

        scope = RowScopeService(db, RBAC(), MetaRegistry(), WorkflowRepository())
        for user, expected_project, expected_task in (
            (supervisor_a, "supervisor-project-a", "supervisor-task-a"),
            (supervisor_b, "supervisor-project-b", "supervisor-task-b"),
        ):
            projects_query = await scope.apply_scope_to_query(
                select(Project),
                Project,
                "project",
                user.id,
                [],
                [],
                False,
            )
            tasks_query = await scope.apply_scope_to_query(
                select(Task),
                Task,
                "task",
                user.id,
                [],
                [],
                False,
            )
            assert {
                row.id for row in (await db.scalars(projects_query)).all()
            } == {expected_project}
            assert {row.id for row in (await db.scalars(tasks_query)).all()} == {
                expected_task
            }

        spoofed_scope = RowScopeService(
            db,
            RBAC(),
            MetaRegistry(),
            WorkflowRepository(),
            requested_workspace_id="workspace-bahandi",
        )
        with pytest.raises(ForbiddenError, match="not assigned"):
            await spoofed_scope.apply_scope_to_query(
                select(Project),
                Project,
                "project",
                supervisor_a.id,
                [],
                [],
                False,
            )

    await engine.dispose()


@pytest.mark.asyncio
async def test_hr_context_is_global_only_for_directory_and_system_admin_entities(
    client, db_session
):
    from app.main import fastapi_app

    employee = User(
        id=str(uuid4()),
        username="directory-user",
        email="directory-user@example.test",
        full_name="Directory User",
        hashed_password="unused",
        is_active=True,
    )
    db_session.add(employee)
    await db_session.flush()

    async def current_hr():
        return CurrentUser(
            id="hr-without-membership",
            username="hr-user",
            roles=["HR"],
            role_ids=[],
        )

    fastapi_app.dependency_overrides[get_current_user_from_token] = current_hr
    try:
        context = await client.get(
            "/api/workspaces/context",
            headers={"X-Workspace-ID": "workspace-bahandi"},
        )
        assert context.status_code == 200
        data = context.json()["data"]
        assert data["active_workspace_id"] is None
        assert data["is_global"] is False
        assert data["capabilities"]["can_manage_payroll"] is True
        assert data["capabilities"]["can_view_hr_directory"] is True
        assert data["capabilities"]["can_view_all_workspaces"] is False

        directory = await client.get("/api/workspaces/hr-directory?page=1")
        assert directory.status_code == 200
        assert directory.json()["total"] == 1

        assert (await client.get("/api/admin/users")).status_code == 403
        assert (await client.get("/api/audit-log")).status_code == 403
        assert (await client.get("/api/entity/user/list")).status_code == 403
    finally:
        fastapi_app.dependency_overrides.pop(get_current_user_from_token, None)


@pytest.mark.asyncio
async def test_seeded_persona_permissions_remove_legacy_system_grants():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as db:
        hr = Role(id="hr-role", name="HR", is_active=True)
        db.add(hr)
        await db.flush()
        db.add(
            EntityPermission(
                id="legacy-hr-user-permission",
                role_id=hr.id,
                entity_name="user",
                can_read=True,
                can_create=True,
                can_update=True,
                can_delete=True,
                can_select=True,
                can_export=True,
                can_import=True,
                in_sidebar=True,
                row_scope="all",
            )
        )
        db.add(
            EntityPermission(
                id="legacy-hr-task-permission",
                role_id=hr.id,
                entity_name="task",
                can_read=True,
                can_create=True,
                can_update=True,
                can_delete=True,
                can_select=True,
                can_export=True,
                can_import=True,
                in_sidebar=True,
                row_scope="all",
            )
        )
        await db.commit()

        await seed_roles(db)
        await seed_entity_permissions(db)
        await seed_entity_permissions(db)
        hr = await db.get(Role, "hr-role")
        hr_permission = await db.scalar(
            select(EntityPermission).where(
                EntityPermission.role_id == hr.id,
                EntityPermission.entity_name == "user",
            )
        )
        assert hr_permission is not None
        assert not hr_permission.can_read
        assert not hr_permission.can_create
        hr_task_permission = await db.scalar(
            select(EntityPermission).where(
                EntityPermission.role_id == hr.id,
                EntityPermission.entity_name == "task",
            )
        )
        assert hr_task_permission is not None
        assert not hr_task_permission.can_read

        employee = await db.scalar(select(Role).where(Role.name == "Employee"))
        admin = await db.scalar(select(Role).where(Role.name == "Administrator"))
        rbac = RBACAppService(AuthRepository(db))
        assert not await rbac.check_permission(
            user_id="hr-user",
            entity="user",
            action="read",
            role_ids=[hr.id],
        )
        assert await rbac.check_permission(
            user_id="admin-user",
            entity="ledger",
            action="read",
            role_ids=[admin.id],
        )
        assert await rbac.check_permission(
            user_id="employee-user",
            entity="task_submission",
            action="create",
            role_ids=[employee.id],
        )

    await engine.dispose()
