"""
Seed: Entity Permissions
========================
Creates the default role-entity permission matrix.
Idempotent — skips existing role+entity combinations.

SystemManager  → full CRUD + admin entities + in_sidebar
Technician     → CRUD on operational entities (no admin), in_sidebar
Viewer         → read-only on operational entities, in_sidebar
HR             → payroll operations + read-only ledger, no operational entities
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.seeds import SeedResult
from app.core.constants.permissions import ROW_SCOPE_ALL
from app.core.framework.models.auth import Role, EntityPermission

# All entities that appear in the sidebar for operational modules.
# In the barebones backend no operational modules are installed; add entities
# here when business modules are reintroduced.
OPERATIONAL_ENTITIES: list[str] = [
    "project",
    "project_member",
    "task_type",
    "task_category",
    "task",
    "task_assignment",
    "task_submission",
    "task_approval",
    "task_link",
    "planner_event",
    "schedule_series",
    "schedule_occurrence",
    "workspace_resource",
    "workspace_team",
    "resource_booking",
]

# Entities only SystemManager can access
ADMIN_ENTITIES = [
    "user",
    "role",
    "entity_permission",
    "audit_log",
    "oc_audit_log",
    "error_log",
    "api_key",
    "user_session",
    "model",
    "model_definition",
    "entity_definition",
    "workflow",
    "workflow_state",
    "workflow_action",
    "workflow_state_link",
    "workflow_transition",
    "module_order",
    "entity_order",
    "user_task_rate",
]

# Payroll entities — access is governed by per-role grants matching each
# entity's declared "rbac" block: admins get full control, HR gets payroll
# operations and read-only ledger access, other roles get nothing.
PAYROLL_ENTITIES = [
    "payroll_period",
    "payroll_settings",
    "payroll_entry",
    "payroll_line_item",
    "invoice",
    "ledger",
]

_FULL = dict(
    can_read=True, can_create=True, can_update=True, can_delete=True,
    can_select=True, can_export=True, can_import=True, in_sidebar=True,
    row_scope=ROW_SCOPE_ALL,
)
_CRUD = dict(
    can_read=True, can_create=True, can_update=True, can_delete=False,
    can_select=True, can_export=True, can_import=False, in_sidebar=True,
    row_scope=ROW_SCOPE_ALL,
)
_READ = dict(
    can_read=True, can_create=False, can_update=False, can_delete=False,
    can_select=True, can_export=True, can_import=False, in_sidebar=True,
    row_scope=ROW_SCOPE_ALL,
)
_NONE = dict(
    can_read=False, can_create=False, can_update=False, can_delete=False,
    can_select=False, can_export=False, can_import=False, in_sidebar=False,
    row_scope=ROW_SCOPE_ALL,
)
_PAYROLL_OPS = dict(
    can_read=True, can_create=True, can_update=True, can_delete=False,
    can_select=True, can_export=True, can_import=False, in_sidebar=True,
    row_scope=ROW_SCOPE_ALL,
)


async def seed_entity_permissions(db: AsyncSession) -> SeedResult:
    """Create default entity permissions per role. Skips existing role+entity combos."""
    result = SeedResult(entity="EntityPermission")

    roles_result = await db.execute(select(Role))
    roles = {r.name: r for r in roles_result.scalars().all()}

    non_admin_role_ids = [
        role.id
        for role in roles.values()
        if role.name not in {"SystemManager", "Administrator"}
    ]
    if non_admin_role_ids:
        legacy_admin_grants = await db.scalars(
            select(EntityPermission).where(
                EntityPermission.role_id.in_(non_admin_role_ids),
                EntityPermission.entity_name.in_(ADMIN_ENTITIES),
            )
        )
        for permission in legacy_admin_grants:
            for field, value in _NONE.items():
                setattr(permission, field, value)
    hr_role = roles.get("HR")
    if hr_role:
        # HR gets global read-only visibility on operational entities.
        # Re-assert _READ on existing rows so DBs seeded by older versions
        # (which zeroed these grants) self-heal on the next seed run.
        hr_operational_grants = await db.scalars(
            select(EntityPermission).where(
                EntityPermission.role_id == hr_role.id,
                EntityPermission.entity_name.in_(OPERATIONAL_ENTITIES),
            )
        )
        for permission in hr_operational_grants:
            for field, value in _READ.items():
                setattr(permission, field, value)

    permission_matrix = []

    # System admins: full access to all (operational + admin)
    for system_admin_name in ("SystemManager", "Administrator"):
        system_admin = roles.get(system_admin_name)
        if not system_admin:
            continue
        for entity in OPERATIONAL_ENTITIES + ADMIN_ENTITIES + PAYROLL_ENTITIES:
            permission_matrix.append((system_admin, entity, _FULL))

    # Workspace supervisors: operational CRUD, no system administration.
    for supervisor_name in ("ProjectManager", "Technician"):
        supervisor = roles.get(supervisor_name)
        if not supervisor:
            continue
        for entity in OPERATIONAL_ENTITIES:
            permission_matrix.append((supervisor, entity, _CRUD))

    # Workspace employees can read operational records and submit assigned work.
    employee = roles.get("Employee")
    if employee:
        for entity in OPERATIONAL_ENTITIES:
            permission_matrix.append(
                (
                    employee,
                    entity,
                    {
                        **_READ,
                        "can_create": entity == "task_submission",
                        "in_sidebar": entity
                        in {"project", "task", "task_submission"},
                    },
                )
            )

    viewer = roles.get("Viewer")
    if viewer:
        for entity in OPERATIONAL_ENTITIES:
            permission_matrix.append((viewer, entity, _READ))

    # HR: global read-only on operational entities plus payroll operations
    # as declared in each entity's "rbac" block (read/create/update on
    # payroll records, read-only on the ledger).
    if hr_role:
        for entity in OPERATIONAL_ENTITIES:
            permission_matrix.append((hr_role, entity, _READ))
        for entity in PAYROLL_ENTITIES:
            perms = _READ if entity == "ledger" else _PAYROLL_OPS
            permission_matrix.append((hr_role, entity, perms))

    for role, entity_name, perms in permission_matrix:
        existing = await db.execute(
            select(EntityPermission)
            .where(EntityPermission.role_id == role.id)
            .where(EntityPermission.entity_name == entity_name)
        )
        existing_permission = existing.scalar_one_or_none()
        if existing_permission:
            if role.name in {"SystemManager", "Administrator"}:
                for field, value in perms.items():
                    setattr(existing_permission, field, value)
            elif entity_name in ADMIN_ENTITIES:
                for field, value in _NONE.items():
                    setattr(existing_permission, field, value)
            result.skipped += 1
            continue

        db.add(EntityPermission(role_id=role.id, entity_name=entity_name, **perms))
        result.created += 1

    await db.commit()
    return result
