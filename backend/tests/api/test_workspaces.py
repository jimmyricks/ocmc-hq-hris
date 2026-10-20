from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.database import Base
from app.core.exceptions import ForbiddenError
from app.core.framework.models.auth import User
from app.application.services.access_control.row_scope_service import RowScopeService
from app.modules.project_tasks.models import Project, ProjectMember, Task
from app.modules.workspaces.models import Workspace, WorkspaceMembership, WorkspaceTeam
from app.modules.workspaces.services import WorkspaceService


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

    await engine.dispose()


@pytest.mark.asyncio
async def test_workspace_query_scope_includes_home_and_project_membership_only():
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
                    title="Home task",
                ),
                Task(
                    id="cross-task",
                    project_id=cross_project.id,
                    title="Cross-company task",
                ),
                Task(
                    id="unmapped-task",
                    project_id=unmapped_project.id,
                    title="Unmapped task",
                ),
            ]
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
        assert {project.id for project in projects} == {
            "home-project",
            "cross-project",
        }

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
        assert {task.id for task in tasks} == {"home-task", "cross-task"}

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
