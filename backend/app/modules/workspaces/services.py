from dataclasses import dataclass
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError, ForbiddenError, NotFoundError
from app.core.framework.models.auth import User
from app.core.serialization import record_to_dict
from app.modules.collaboration_audit.services import AuditLogService
from app.modules.workspaces.models import Workspace, WorkspaceMembership, WorkspaceTeam


WORKSPACE_DEFAULTS = (
    {
        "id": "workspace-one-heart",
        "name": "One Heart Creative Studios",
        "slug": "one-heart-creative-studios",
        "color": "#d946ef",
    },
    {
        "id": "workspace-fourth-street",
        "name": "4th Street Recording Studio",
        "slug": "fourth-street-recording-studio",
        "color": "#0ea5e9",
    },
    {
        "id": "workspace-oc-music-school",
        "name": "OC Music School",
        "slug": "oc-music-school",
        "color": "#22c55e",
    },
    {
        "id": "workspace-bahandi",
        "name": "Bahandi Entertainment",
        "slug": "bahandi-entertainment",
        "color": "#f97316",
    },
)

ADMIN_ROLES = {"Administrator", "SystemManager"}
HR_ROLES = {"HR"}


@dataclass(frozen=True)
class WorkspaceContext:
    workspace_ids: tuple[str, ...]
    active_workspace_id: str | None
    is_global: bool = False


class WorkspaceService:
    @staticmethod
    def is_system_admin(roles: list[str], is_superuser: bool) -> bool:
        return is_superuser or bool(ADMIN_ROLES.intersection(roles or []))

    @staticmethod
    def is_admin(roles: list[str], is_superuser: bool) -> bool:
        return WorkspaceService.is_system_admin(roles, is_superuser)

    @staticmethod
    def is_hr(roles: list[str]) -> bool:
        return bool(HR_ROLES.intersection(roles or []))

    @staticmethod
    def is_payroll_admin(roles: list[str], is_superuser: bool) -> bool:
        return WorkspaceService.is_system_admin(roles, is_superuser) or WorkspaceService.is_hr(
            roles
        )

    @staticmethod
    async def seed_defaults(db: AsyncSession) -> None:
        for data in WORKSPACE_DEFAULTS:
            workspace = await db.scalar(
                select(Workspace).where(Workspace.slug == data["slug"])
            )
            if workspace is None:
                db.add(Workspace(**data, timezone="UTC", is_active=True))
        await db.flush()

        bahandi = await db.scalar(
            select(Workspace).where(Workspace.slug == "bahandi-entertainment")
        )
        if bahandi:
            for name, slug in (
                ("Social Media Management", "social-media-management"),
                ("Artist Management", "artist-management"),
            ):
                team = await db.scalar(
                    select(WorkspaceTeam).where(
                        WorkspaceTeam.workspace_id == bahandi.id,
                        WorkspaceTeam.slug == slug,
                    )
                )
                if team is None:
                    db.add(
                        WorkspaceTeam(
                            id=f"bahandi-{slug}",
                            workspace_id=bahandi.id,
                            name=name,
                            slug=slug,
                        )
                    )
        await db.commit()

    @staticmethod
    async def resolve_context(
        db: AsyncSession,
        user_id: str,
        roles: list[str],
        is_superuser: bool,
        requested_workspace_id: str | None = None,
    ) -> WorkspaceContext:
        if WorkspaceService.is_system_admin(roles, is_superuser):
            if not requested_workspace_id or requested_workspace_id == "all":
                return WorkspaceContext((), None, is_global=True)
            workspace = await db.get(Workspace, requested_workspace_id)
            if not workspace or not workspace.is_active:
                raise NotFoundError("Workspace", requested_workspace_id)
            return WorkspaceContext((workspace.id,), workspace.id)

        if WorkspaceService.is_hr(roles):
            return WorkspaceContext((), None)

        if requested_workspace_id == "all":
            raise ForbiddenError("Only system administrators can select all workspaces")

        result = await db.execute(
            select(WorkspaceMembership, Workspace)
            .join(Workspace, Workspace.id == WorkspaceMembership.workspace_id)
            .where(
                WorkspaceMembership.user_id == user_id,
                WorkspaceMembership.is_active.is_(True),
                Workspace.is_active.is_(True),
            )
        )
        memberships = result.all()
        if not memberships:
            raise ForbiddenError("You are not assigned to an active workspace")

        home = next(
            (membership for membership, _ in memberships if membership.is_home),
            None,
        )
        if not home:
            raise ForbiddenError("An active home workspace has not been assigned")

        if requested_workspace_id:
            matching = next(
                (
                    membership
                    for membership, _ in memberships
                    if membership.workspace_id == requested_workspace_id
                ),
                None,
            )
            if matching is None:
                raise ForbiddenError("You are not assigned to this workspace")
            if matching.membership_role != "supervisor" and matching.id != home.id:
                raise ForbiddenError("Members cannot switch their home workspace")
            return WorkspaceContext((matching.workspace_id,), matching.workspace_id)

        return WorkspaceContext((home.workspace_id,), home.workspace_id)

    @staticmethod
    async def visible_workspaces(
        db: AsyncSession,
        user_id: str,
        roles: list[str],
        is_superuser: bool,
    ) -> list[Workspace]:
        if WorkspaceService.is_admin(roles, is_superuser):
            result = await db.execute(
                select(Workspace).where(Workspace.is_active.is_(True)).order_by(Workspace.name)
            )
            return list(result.scalars().all())

        result = await db.execute(
            select(Workspace)
            .join(
                WorkspaceMembership,
                WorkspaceMembership.workspace_id == Workspace.id,
            )
            .where(
                WorkspaceMembership.user_id == user_id,
                WorkspaceMembership.is_active.is_(True),
                Workspace.is_active.is_(True),
            )
            .order_by(Workspace.name)
        )
        return list(result.scalars().unique().all())

    @staticmethod
    async def require_workspace_role(
        db: AsyncSession,
        user: object,
        workspace_id: str,
        required_role: str,
        requested_workspace_id: str | None = None,
    ) -> None:
        roles = getattr(user, "roles", []) or []
        is_superuser = bool(getattr(user, "is_superuser", False))
        if WorkspaceService.is_admin(roles, is_superuser):
            return
        context = await WorkspaceService.resolve_context(
            db,
            user.id,
            roles,
            is_superuser,
            requested_workspace_id,
        )
        if context.active_workspace_id != workspace_id:
            raise ForbiddenError("The record is outside your active workspace")
        membership_role = await db.scalar(
            select(WorkspaceMembership.membership_role).where(
                WorkspaceMembership.workspace_id == workspace_id,
                WorkspaceMembership.user_id == user.id,
                WorkspaceMembership.is_active.is_(True),
            )
        )
        if membership_role != required_role:
            raise ForbiddenError(f"This action requires the {required_role} workspace role")

    @staticmethod
    async def assign_membership(
        db: AsyncSession,
        workspace_id: str,
        user_id: str,
        membership_role: str,
        is_home: bool,
        actor_id: str,
    ) -> WorkspaceMembership:
        if membership_role not in {"member", "supervisor"}:
            raise BadRequestError("membership_role must be member or supervisor")
        if membership_role == "member" and not is_home:
            raise BadRequestError("Member assignments must be the user's home workspace")
        workspace = await db.get(Workspace, workspace_id)
        user = await db.get(User, user_id)
        if not workspace or not workspace.is_active:
            raise NotFoundError("Workspace", workspace_id)
        if not user:
            raise NotFoundError("User", user_id)

        existing = await db.scalar(
            select(WorkspaceMembership).where(
                WorkspaceMembership.workspace_id == workspace_id,
                WorkspaceMembership.user_id == user_id,
            )
        )
        current_home = await db.scalar(
            select(WorkspaceMembership).where(
                WorkspaceMembership.user_id == user_id,
                WorkspaceMembership.is_home.is_(True),
                WorkspaceMembership.id != (existing.id if existing else ""),
            )
        )
        if existing and existing.is_home and not is_home:
            raise BadRequestError("Remove the current home assignment before changing it")
        if not is_home and not current_home and not (existing and existing.is_home):
            raise BadRequestError("The first workspace assignment must be the home workspace")
        if is_home:
            if current_home:
                raise BadRequestError("The user already has a home workspace")

        old_values = record_to_dict(existing) if existing else None
        if existing:
            existing.membership_role = membership_role
            existing.is_home = is_home
            existing.is_active = True
            existing.last_modified_by = actor_id
            record = existing
        else:
            record = WorkspaceMembership(
                id=str(uuid4()),
                workspace_id=workspace_id,
                user_id=user_id,
                membership_role=membership_role,
                is_home=is_home,
                is_active=True,
                created_by=actor_id,
                last_modified_by=actor_id,
            )
            db.add(record)
        await AuditLogService.log_event(
            db,
            entity="workspace_membership",
            record_id=record.id,
            action="create" if old_values is None else "update",
            actor_id=actor_id,
            old_values=old_values,
            new_values=record_to_dict(record),
        )
        await db.commit()
        await db.refresh(record)
        return record
