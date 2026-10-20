"""
Filter SQL Builder
==================

Translates a list of :class:`~app.api.schemas.filter_clause.FilterClause` into
a parameterized SQLAlchemy ``WHERE`` expression, with column / operator
whitelisting and value token resolution.

This is the *only* place the wire-format contract meets SQL.  Every consumer
in the list endpoint (and any future server-side filter consumer) should
funnel through :func:`clause_to_sqlalchemy`.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Iterable, Optional

from sqlalchemy import or_
from sqlalchemy.sql import ColumnElement
from sqlalchemy.sql.sqltypes import (
    Boolean,
    Date,
    DateTime,
    Integer,
    Numeric,
    String,
    Text,
)

from app.api.schemas.filter_clause import (
    FilterClause,
    FilterOp,
    resolve_token,
)


class FilterValidationError(ValueError):
    """Raised when a clause references an unknown field/operator or its
    value cannot be coerced to the column type.

    The list endpoint maps this to ``ActionResponse(status="error", ...)``
    to match the existing defensive style for ``filter_field``.
    """


def _coerce_scalar_value(value: Any, col_type: Any) -> Any:
    """Best-effort coercion of a scalar ``value`` to a Python type compatible
    with the SQLAlchemy column type.

    Coercion rules:
      * ``Date`` columns accept ``date`` and ISO-8601 ``"YYYY-MM-DD"`` strings.
      * ``DateTime`` columns accept ``datetime`` and ISO-8601 strings.
      * ``Integer`` columns accept ints and numeric strings.
      * ``Numeric``/``Float`` columns accept numbers and numeric strings.
      * ``Boolean`` columns accept bools, ``"true"``/``"false"`` (case-insensitive).
      * ``String``/``Text`` columns accept any value (cast to ``str``).
    """
    if value is None:
        return None

    if isinstance(col_type, (Date, DateTime)):
        if isinstance(value, (date, datetime)):
            return value
        if isinstance(value, str) and value:
            try:
                if isinstance(col_type, DateTime):
                    return datetime.fromisoformat(value)
                return date.fromisoformat(value)
            except ValueError:
                raise FilterValidationError(
                    f"value {value!r} is not a valid ISO-8601 "
                    f"{'datetime' if isinstance(col_type, DateTime) else 'date'}"
                )
        raise FilterValidationError(
            f"value {value!r} is not coercible to "
            f"{'datetime' if isinstance(col_type, DateTime) else 'date'}"
        )

    if isinstance(col_type, Integer):
        if isinstance(value, bool):
            raise FilterValidationError("booleans are not valid for integer columns")
        if isinstance(value, int) and not isinstance(value, bool):
            return value
        if isinstance(value, str) and value:
            try:
                return int(value)
            except ValueError as exc:
                raise FilterValidationError(
                    f"value {value!r} is not a valid integer"
                ) from exc
        raise FilterValidationError(f"value {value!r} is not a valid integer")

    if isinstance(col_type, Numeric):
        if isinstance(value, bool):
            raise FilterValidationError("booleans are not valid for numeric columns")
        if isinstance(value, (int, float)):
            return value
        if isinstance(value, str) and value:
            try:
                return float(value)
            except ValueError as exc:
                raise FilterValidationError(
                    f"value {value!r} is not a valid number"
                ) from exc
        raise FilterValidationError(f"value {value!r} is not a valid number")

    if isinstance(col_type, Boolean):
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in ("true", "1", "yes"):
                return True
            if lowered in ("false", "0", "no"):
                return False
        raise FilterValidationError(
            f"value {value!r} is not a valid boolean"
        )

    if isinstance(col_type, (String, Text)):
        return str(value)

    # Unknown column type — fall back to letting SQLAlchemy handle it.
    return value


def _coerce_value(value: Any, col_type: Any, *, in_list: bool) -> Any:
    """Coerce ``value`` for the given column type, with list support."""
    if in_list:
        if not isinstance(value, (list, tuple)):
            value = [value]
        return [_coerce_scalar_value(item, col_type) for item in value]
    return _coerce_scalar_value(value, col_type)


def _build_expression(
    col: ColumnElement, op: FilterOp, value: Any, *, col_type: Any
) -> ColumnElement:
    """Build a single :class:`ColumnElement` for one operator/value pair.

    Assumes the value has already been token-resolved and coerced.
    """
    if op == FilterOp.EQ:
        return col == value
    if op == FilterOp.NE:
        # NULL-safe not-equal: a NULL field should *not* match the literal,
        # so the row is excluded from the "ne" set.  Mirrors the dashboard
        # repo's `LOWER(COALESCE(workflow_state,'')) != 'closed'` semantics
        # where NULL is treated as not-closed (excluded from overdue set).
        return or_(col.is_(None), col != value)
    if op == FilterOp.LT:
        return col < value
    if op == FilterOp.LTE:
        return col <= value
    if op == FilterOp.GT:
        return col > value
    if op == FilterOp.GTE:
        return col >= value
    if op == FilterOp.IN:
        if not value:
            return col.in_([])
        return col.in_(value)
    if op == FilterOp.NIN:
        if not value:
            return col.notin_([])
        return ~col.in_(value)
    if op == FilterOp.LIKE:
        if not isinstance(value, str):
            raise FilterValidationError("'like' requires a string value")
        return col.ilike(f"%{value}%")
    if op == FilterOp.IS_NULL:
        if isinstance(value, str):
            lowered = value.strip().lower()
            coerced = lowered in ("true", "1", "yes")
        else:
            coerced = bool(value)
        return col.is_(None) if coerced else col.is_not(None)

    raise FilterValidationError(f"unsupported operator: {op!r}")


def clause_to_sqlalchemy(
    model: type,
    clause: FilterClause,
    *,
    selectable_columns: Iterable[str],
    user: Any = None,
    case_insensitive_string_ops: bool = False,
) -> ColumnElement:
    """Translate one :class:`FilterClause` into a SQLAlchemy expression.

    Args:
        model: SQLAlchemy ORM model class
        clause: parsed :class:`FilterClause`
        selectable_columns: iterable of real column names on ``model.__table__``
            — anything outside this set is rejected
        user: the authenticated user (or ``None``); passed to
            :func:`resolve_token` so ``$current_user`` resolves
        case_insensitive_string_ops: if ``True``, string comparisons use
            ``func.lower(col)`` for ``eq``/``ne``/``in``/``nin``/``like``.
            The dashboard's overdue predicate uses
            ``LOWER(COALESCE(workflow_state,'')) != 'closed'``; flip this
            on for state-style fields to match that semantics.

    Returns:
        A :class:`ColumnElement` suitable for ``query.where(...)``.

    Raises:
        FilterValidationError: on unknown field, unknown op, or value type
            mismatch.
    """
    selectable = set(selectable_columns)
    if clause.field not in selectable:
        raise FilterValidationError(
            f"Invalid filter field '{clause.field}'"
        )

    if not hasattr(model, clause.field):
        raise FilterValidationError(
            f"Invalid filter field '{clause.field}'"
        )

    col = getattr(model, clause.field)
    col_type = col.type

    # Resolve tokens first, then coerce to column type.
    is_list_op = clause.op in (FilterOp.IN, FilterOp.NIN)
    if clause.op == FilterOp.IS_NULL:
        # is_null takes a boolean — no type coercion needed
        raw_value: Any = clause.value
        coerced = raw_value
    elif is_list_op:
        raw_value = clause.value
        if not isinstance(raw_value, (list, tuple)):
            raw_value = [raw_value]
        raw_value = [resolve_token(v, user=user) for v in raw_value]
        try:
            coerced = _coerce_value(raw_value, col_type, in_list=True)
        except FilterValidationError:
            raise
        except Exception as exc:  # pragma: no cover — defensive
            raise FilterValidationError(str(exc)) from exc
    else:
        raw_value = resolve_token(clause.value, user=user)
        try:
            coerced = _coerce_value(raw_value, col_type, in_list=False)
        except FilterValidationError:
            raise
        except Exception as exc:  # pragma: no cover — defensive
            raise FilterValidationError(str(exc)) from exc

    # Optional case-insensitive string normalization to match the dashboard
    # repo's `LOWER(COALESCE(workflow_state, ''))` pattern.  We do not wrap
    # with COALESCE here — NULL is a deliberate, queryable value — so
    # callers opt in only when they want label-style fields treated
    # case-insensitively (e.g. workflow_state slugs).
    if case_insensitive_string_ops and isinstance(col_type, (String, Text)):
        from sqlalchemy import func
        from sqlalchemy.sql.elements import ColumnElement as _CE

        if clause.op == FilterOp.LIKE:
            # LIKE already uses ilike; nothing to do.
            return _build_expression(col, clause.op, coerced, col_type=col_type)
        if clause.op in (FilterOp.EQ, FilterOp.NE, FilterOp.IN, FilterOp.NIN):
            lower_col = func.lower(col)
            if clause.op == FilterOp.NE:
                # Preserve the NULL-safe semantics.
                return or_(col.is_(None), lower_col != func.lower(coerced))
            if clause.op in (FilterOp.IN, FilterOp.NIN):
                lowered = [func.lower(v) for v in coerced]
                if clause.op == FilterOp.IN:
                    return lower_col.in_(lowered)
                return ~lower_col.in_(lowered)
            return lower_col == func.lower(coerced)

    return _build_expression(col, clause.op, coerced, col_type=col_type)


def build_clause_list(
    model: type,
    clauses: list[FilterClause],
    *,
    selectable_columns: Iterable[str],
    user: Any = None,
    case_insensitive_string_fields: Optional[set[str]] = None,
) -> list[ColumnElement]:
    """Translate a list of clauses into a list of SQLAlchemy expressions.

    No AND-combining here — the caller (the list endpoint) decides how to
    combine.  The expressions are returned in input order.

    Args:
        case_insensitive_string_fields: set of field names whose comparisons
            should be case-insensitive (matches the dashboard repo's
            ``LOWER(COALESCE(...))`` style for state fields).
    """
    case_set = case_insensitive_string_fields or set()
    return [
        clause_to_sqlalchemy(
            model,
            clause,
            selectable_columns=selectable_columns,
            user=user,
            case_insensitive_string_ops=clause.field in case_set,
        )
        for clause in clauses
    ]


__all__ = [
    "FilterValidationError",
    "clause_to_sqlalchemy",
    "build_clause_list",
]
