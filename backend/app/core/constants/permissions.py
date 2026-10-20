"""Canonical permission constants for the permission row-scope restructure."""

ROW_SCOPE_ALL = "all"
ROW_SCOPE_OWNER_ONLY = "owner_only"
ROW_SCOPE_OWNER_OR_ASSIGNED = "owner_or_assigned"

# Pseudo-role token used in workflow transition allowed_roles to mean "record owner".
# Stored namespaced so it cannot collide with an actual RBAC role named "Owner".
RESERVED_ROLE_OWNER = "$owner"

# Legacy tokens that still resolve to the owner pseudo-role for back-compat.
_OWNER_ALIAS = {RESERVED_ROLE_OWNER, "Owner"}

PERMISSION_FLAGS = [
    "can_read",
    "can_create",
    "can_update",
    "can_delete",
    "can_select",
    "can_export",
    "can_import",
    "in_sidebar",
]


def merge_scope(current: str | list[str] | None, incoming: str | list[str] | None) -> list[str]:
    """Combine two scope values into a list of unique scopes.

    This does not rank scopes (e.g., "all" vs "owner_only"). It collects the
    filters from both roles so the enforcement layer can OR them together. This
    keeps the model extensible: future scopes like "same_department" can be
    added without needing a total ordering.
    """
    def _to_list(value):
        if value is None:
            return []
        if isinstance(value, list):
            return [v for v in value if v]
        return [value] if value else []

    combined = _to_list(current) + _to_list(incoming)
    # Preserve insertion order while removing duplicates.
    return list(dict.fromkeys(combined))


def can_act_on_transition(
    allowed_roles: list[str],
    user_roles: list[str],
    created_by: str,
    current_user_id: str,
) -> bool:
    """Check if a user can perform a workflow transition.

    A reserved owner token matches when the current user is the record owner.
    Real role names are matched against the user's role set.
    An empty allowed_roles list means the transition is unrestricted.
    """
    allowed = set(allowed_roles or [])
    if not allowed:
        return True
    if (allowed & _OWNER_ALIAS) and created_by == current_user_id:
        return True
    return bool(set(user_roles) & allowed)
