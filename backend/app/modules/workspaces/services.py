from dataclasses import dataclass
from typing import Any
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

        # HR resolves globally: read visibility spans all workspaces.
        if WorkspaceService.is_hr(roles):
            return WorkspaceContext((), None, is_global=True)

        if requested_workspace_id == "all":
            raise ForbiddenError("Only system administrators can select all workspaces")

        result = await db.execute(
            select(WorkspaceMembership, Workspace)
            .join(Workspace, Workspace.id == WorkspaceMembership.workspace_id)
            .where(
                WorkspaceMembership.user_id == user_id,
                WorkspaceMembership.membership_role == "supervisor",
                WorkspaceMembership.is_active.is_(True),
                Workspace.is_active.is_(True),
            )
            .order_by(Workspace.name)
        )
        memberships = result.all()
        if not memberships:
            return WorkspaceContext((), None)

        home = next(
            (membership for membership, _ in memberships if membership.is_home),
            None,
        )
        if not home:
            home = memberships[0][0]

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
                WorkspaceMembership.membership_role == "supervisor",
                WorkspaceMembership.is_active.is_(True),
                Workspace.is_active.is_(True),
            )
            .order_by(Workspace.name)
        )
        return list(result.scalars().unique().all())

    @staticmethod
    async def get_context_payload(
        db: AsyncSession,
        user: Any,
        requested_workspace_id: str | None = None,
    ) -> dict[str, Any]:
        """Build the workspace/capability payload consumed by the frontend shell."""
        roles = getattr(user, "roles", []) or []
        is_superuser = bool(getattr(user, "is_superuser", False))
        user_id = str(getattr(user, "id"))

        context = await WorkspaceService.resolve_context(
            db,
            user_id,
            roles,
            is_superuser,
            requested_workspace_id,
        )
        workspaces = await WorkspaceService.visible_workspaces(
            db, user_id, roles, is_superuser
        )
        memberships = (
            await db.scalars(
                select(WorkspaceMembership)
                .join(Workspace, Workspace.id == WorkspaceMembership.workspace_id)
                .where(
                    WorkspaceMembership.user_id == user_id,
                    WorkspaceMembership.membership_role == "supervisor",
                    WorkspaceMembership.is_active.is_(True),
                    Workspace.is_active.is_(True),
                )
            )
        ).all()
        memberships_by_workspace = {
            membership.workspace_id: membership for membership in memberships
        }
        active_membership = memberships_by_workspace.get(context.active_workspace_id)
        active_role = active_membership.membership_role if active_membership else None
        is_system_admin = WorkspaceService.is_system_admin(roles, is_superuser)
        capabilities = {
            "can_view_all_workspaces": is_system_admin,
            "can_manage_active_workspace": is_system_admin or active_role == "supervisor",
            "can_manage_payroll": WorkspaceService.is_payroll_admin(roles, is_superuser),
            "can_view_global_schedule": is_system_admin
            or any(item.membership_role == "supervisor" for item in memberships),
            "can_view_hr_directory": is_system_admin or WorkspaceService.is_hr(roles),
            "is_system_admin": is_system_admin,
        }

        def workspace_dict(workspace: Workspace) -> dict[str, Any]:
            membership = memberships_by_workspace.get(workspace.id)
            return {
                "id": workspace.id,
                "name": workspace.name,
                "slug": workspace.slug,
                "color": workspace.color,
                "timezone": workspace.timezone,
                "is_active": workspace.is_active,
                "membership_role": membership.membership_role if membership else None,
                "is_home": bool(membership and membership.is_home),
                "can_manage": is_system_admin
                or bool(membership and membership.membership_role == "supervisor"),
            }

        workspace_rows = [workspace_dict(workspace) for workspace in workspaces]

        return {
            "active_workspace_id": context.active_workspace_id,
            "home_workspace_id": next(
                (membership.workspace_id for membership in memberships if membership.is_home),
                None,
            ),
            "is_global": context.is_global,
            "can_manage": capabilities["can_manage_active_workspace"],
            "capabilities": capabilities,
            "manageable_workspaces": [
                workspace for workspace in workspace_rows if workspace["can_manage"]
            ],
            "workspaces": workspace_rows,
        }

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
        if membership_role != "supervisor":
            raise BadRequestError("Workspace assignments are only for supervisors")
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
                WorkspaceMembership.is_active.is_(True),
                WorkspaceMembership.id != (existing.id if existing else ""),
            )
        )
        if is_home and current_home:
            raise BadRequestError("The user already has a home workspace")

        old_values = record_to_dict(existing) if existing else None
        if existing:
            existing.membership_role = membership_role
            existing.is_home = is_home or existing.is_home
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
