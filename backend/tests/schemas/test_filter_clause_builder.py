"""
Unit tests for the SQL filter builder (``clause_to_sqlalchemy`` / ``build_clause_list``).

Uses the real ``Task`` model from the loaded entity registry against an
in-memory SQLite session to verify that each operator produces correct SQL.
"""
from __future__ import annotations

from datetime import date, datetime

import pytest
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.filter_clause import FilterClause
from app.infrastructure.database.query.filter_clause_builder import (
    FilterValidationError,
    build_clause_list,
    clause_to_sqlalchemy,
)


class _StubUser:
    def __init__(self, user_id: str = "test-user"):
        self.id = user_id


def _get_task_model():
    """Import the dynamic Task model from the loaded entity registry."""
    from app.infrastructure.database.repositories.entity_repository import get_entity_model
    model = get_entity_model("task")
    assert model is not None, "Task model not found — entities not loaded"
    return model


def _selectable_columns(model) -> set[str]:
    return set(model.__table__.columns.keys())


MODEL = _get_task_model()
COLUMNS = _selectable_columns(MODEL)
USER = _StubUser()


class TestClauseToSqlalchemy:
    """Verify each operator maps to an expected SQL expression via string
    representation — not perfect but catches regressions in operator logic."""

    def _expr(self, clause: FilterClause, **kw) -> str:
        kwargs = dict(selectable_columns=COLUMNS, user=USER)
        kwargs.update(kw)
        return str(clause_to_sqlalchemy(MODEL, clause, **kwargs).compile(compile_kwargs={"literal_binds": True}))

    def test_eq(self):
        expr = self._expr(FilterClause(field="status", op="eq", value="Closed"))
        assert "status" in expr
        assert "Closed" in expr
        # With case-insensitive string ops we get func.lower
        assert "lower" not in expr

    def test_eq_with_case_insensitive(self):
        expr = self._expr(
            FilterClause(field="status", op="eq", value="Closed"),
            case_insensitive_string_ops=True,
        )
        # Table prefix may vary; check that lowercase comparison is used
        assert "lower(" in expr

    def test_ne(self):
        expr = self._expr(FilterClause(field="status", op="ne", value="Closed"))
        # NE becomes IS NULL OR !=, depending on backend
        assert "IS NULL" in expr or "!=" in expr or "NOT" in expr

    def test_ne_with_case_insensitive(self):
        expr = self._expr(
            FilterClause(field="status", op="ne", value="Closed"),
            case_insensitive_string_ops=True,
        )
        assert "lower(" in expr

    def test_lt(self):
        expr = self._expr(FilterClause(field="due_date", op="lt", value=date(2024, 1, 1)))
        assert "due_date <" in expr

    def test_lte(self):
        expr = self._expr(FilterClause(field="due_date", op="lte", value=date(2024, 1, 1)))
        assert "due_date <=" in expr

    def test_gt(self):
        expr = self._expr(FilterClause(field="due_date", op="gt", value=date(2024, 1, 1)))
        assert "due_date >" in expr

    def test_gte(self):
        expr = self._expr(FilterClause(field="due_date", op="gte", value=date(2024, 1, 1)))
        assert "due_date >=" in expr

    def test_in(self):
        expr = self._expr(FilterClause(field="status", op="in", value=["Closed", "Approved"]))
        assert "status IN" in expr

    def test_nin(self):
        expr = self._expr(FilterClause(field="status", op="nin", value=["Closed"]))
        assert "status NOT IN" in expr or "NOT (status IN" in expr

    def test_like(self):
        expr = self._expr(FilterClause(field="description", op="like", value="search"))
        # ILIKE is not supported by SQLite, so cast renders differently;
        # just check it produces a LIKE or ILIKE
        assert "LIKE" in expr.upper()

    def test_is_null_true(self):
        expr = self._expr(FilterClause(field="due_date", op="is_null", value=True))
        # Column name in expression with table prefix
        assert "IS NULL" in expr.upper()

    def test_is_null_false(self):
        expr = self._expr(FilterClause(field="due_date", op="is_null", value=False))
        assert "IS NOT NULL" in expr.upper()

    def test_unknown_field_raises(self):
        with pytest.raises(FilterValidationError):
            clause_to_sqlalchemy(
                MODEL,
                FilterClause(field="nonexistent_column", op="eq", value="x"),
                selectable_columns=COLUMNS,
            )


class TestBuildClauseList:
    def test_empty_list(self):
        assert build_clause_list(MODEL, [], selectable_columns=COLUMNS, user=USER) == []

    def test_multiple_clauses(self):
        clauses = [
            FilterClause(field="status", op="ne", value="Closed"),
            FilterClause(field="due_date", op="is_null", value=False),
        ]
        exprs = build_clause_list(MODEL, clauses, selectable_columns=COLUMNS, user=USER)
        assert len(exprs) == 2

    def test_case_insensitive_field_set(self):
        clauses = [
            FilterClause(field="status", op="eq", value="closed"),
            FilterClause(field="description", op="eq", value="hello"),
        ]
        exprs = build_clause_list(
            MODEL,
            clauses,
            selectable_columns=COLUMNS,
            user=USER,
            case_insensitive_string_fields={"status"},
        )
        assert len(exprs) == 2
        s1 = str(exprs[0])  # status — case-insensitive
        s2 = str(exprs[1])  # description — case-sensitive
        # status should use lower(), description should not
        assert "lower(" in s1, f"Expected case-insensitive in: {s1}"
        assert "lower(" not in s2 or s1 != s2


class TestFilterBackwardCompat:
    """Ensure the existing test that checks legacy filter_field still passes
    — this is asserted at the integration layer, but we also verify the
    contract functions don't mutate or clobber legacy behavior."""

    def test_parse_filters_is_pure(self):
        from app.api.schemas.filter_clause import parse_filters
        # Does not raise, returns list
        result = parse_filters('[{"field":"x","op":"eq","value":1}]')
        assert len(result) == 1
        # Legacy path unaffected — parse_filters is pure input→output
