"""
Filter Contract
===============

Shared filter clause schema for structured server-side list filtering.

A filter is an **array of clauses** that are AND-joined when applied to a query.

Wire format
-----------

Clauses are transported as a single URL-encoded JSON query param named `filters`::

    /work_order?filters=%5B%7B%22field%22%3A%22due_date%22%2C%22op%22%3A%22lt%22%2C%22value%22%3A%22%24today%22%7D%2C...%5D

Decoded, the payload is::

    [
      { "field": "due_date",       "op": "lt", "value": "$today" },
      { "field": "workflow_state", "op": "ne", "value": "closed" }
    ]

Operators
---------

``eq``      equals
``ne``      not equals (NULL-safe — "not equal and not null")
``lt``      less than
``lte``     less than or equal
``gt``      greater than
``gte``     greater than or equal
``in``      in list
``nin``     not in list
``like``    case-insensitive substring
``is_null`` null / not null (boolean value)

Value tokens
------------

``$today``         :class:`datetime.date.today()`
``$now``           :class:`datetime.datetime.utcnow`
``$current_user``  authenticated user id
"""
from __future__ import annotations

import json
from datetime import date, datetime
from enum import Enum
from typing import Any, Callable, Optional

from pydantic import BaseModel, Field, ValidationError, field_validator


class FilterOp(str, Enum):
    """Supported filter operators.

    The string values are the canonical wire format.  All operators are
    case-insensitive on parse (values are normalized to lowercase).
    """

    EQ = "eq"
    NE = "ne"
    LT = "lt"
    LTE = "lte"
    GT = "gt"
    GTE = "gte"
    IN = "in"
    NIN = "nin"
    LIKE = "like"
    IS_NULL = "is_null"


# Closed set of valid operator tokens (lowercased).  Used by the SQL builder
# to reject anything not in this set even before validating values.
VALID_OPS: frozenset[str] = frozenset(op.value for op in FilterOp)
# Convenience list (ordered, mirrors FilterOp declaration order).
FILTER_OPS: list[str] = [op.value for op in FilterOp]


class FilterClauseError(ValueError):
    """Raised when the ``filters`` query param cannot be parsed."""

    def __init__(self, message: str, *, raw: Optional[str] = None):
        super().__init__(message)
        self.raw = raw


class FilterClause(BaseModel):
    """A single filter clause.

    Attributes:
        field: column/field name on the target entity
        op: filter operator (one of :class:`FilterOp`)
        value: filter value; can be a scalar, a list, or a server token
    """

    field: str = Field(..., min_length=1)
    op: FilterOp
    value: Any = None

    @field_validator("op", mode="before")
    @classmethod
    def _lowercase_op(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.strip().lower()
        return v

    @field_validator("field")
    @classmethod
    def _non_empty_field(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("field must be a non-empty string")
        return v.strip()


# ---------------------------------------------------------------------------
# Token resolvers
# ---------------------------------------------------------------------------

# Public token names.  Kept module-level so tests / docs can introspect them.
TOKEN_TODAY = "$today"
TOKEN_NOW = "$now"
TOKEN_CURRENT_USER = "$current_user"

# Maps a token name to a callable that resolves it.  ``user`` is passed as a
# keyword argument because all callers in this module receive a
# :class:`app.core.security.CurrentUser` (or None when unauthenticated).
TOKEN_RESOLVERS: dict[str, Callable[..., Any]] = {
    TOKEN_TODAY: lambda **_: date.today(),
    TOKEN_NOW: lambda **_: datetime.utcnow(),
    TOKEN_CURRENT_USER: lambda *, user=None, **_: getattr(user, "id", None),
}


def resolve_token(value: Any, *, user: Any = None) -> Any:
    """Resolve a server-side token in-place.

    Strings beginning with ``$`` are looked up in :data:`TOKEN_RESOLVERS` and
    replaced with the live value.  Anything else is returned untouched.
    Lists/tuples are resolved recursively.  Unknown tokens raise
    :class:`FilterClauseError` so the caller can surface a structured error
    response.
    """
    if isinstance(value, str) and value in TOKEN_RESOLVERS:
        return TOKEN_RESOLVERS[value](user=user)
    if isinstance(value, str) and value.startswith("$"):
        raise FilterClauseError(f"Unknown filter token: {value!r}")
    if isinstance(value, (list, tuple)):
        return [resolve_token(item, user=user) for item in value]
    return value


# ---------------------------------------------------------------------------
# Public parse entrypoint
# ---------------------------------------------------------------------------


def _coerce_clause(raw: Any) -> FilterClause:
    """Coerce a single raw mapping into a :class:`FilterClause`.

    Accepts ``None``/empty mappings and returns an empty clause that callers
    can drop.  Raises :class:`FilterClauseError` on bad shape.
    """
    if not isinstance(raw, dict):
        raise FilterClauseError("each filter clause must be an object")
    try:
        return FilterClause.model_validate(raw)
    except ValidationError as exc:
        raise FilterClauseError(f"invalid filter clause: {exc.errors()}") from exc


def parse_filters(raw: Optional[str]) -> list[FilterClause]:
    """Decode the ``filters`` query param into a list of :class:`FilterClause`.

    ``None`` or empty string returns an empty list.  Malformed JSON or shape
    problems raise :class:`FilterClauseError`.
    """
    if raw is None or raw == "":
        return []
    if not isinstance(raw, str):
        raise FilterClauseError("filters must be a JSON-encoded string")

    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise FilterClauseError(f"filters is not valid JSON: {exc.msg}") from exc

    if decoded is None:
        return []
    if not isinstance(decoded, list):
        raise FilterClauseError("filters must be a JSON array of clauses")

    return [_coerce_clause(item) for item in decoded]


__all__ = [
    "FilterOp",
    "FilterClause",
    "FilterClauseError",
    "VALID_OPS",
    "FILTER_OPS",
    "TOKEN_TODAY",
    "TOKEN_NOW",
    "TOKEN_CURRENT_USER",
    "TOKEN_RESOLVERS",
    "resolve_token",
    "parse_filters",
]
