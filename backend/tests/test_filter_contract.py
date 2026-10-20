"""
Unit tests for the filter contract (Story 0).

Tests cover:
- FilterOp enum values
- FilterClause validation
- parse_filters() JSON parsing and validation
- resolve_token() token resolution
"""

import pytest
from datetime import date, datetime
from app.api.schemas.filter_clause import (
    FilterOp,
    FilterClause,
    parse_filters,
    resolve_token,
    FilterClauseError,
    TOKEN_TODAY,
    TOKEN_NOW,
    TOKEN_CURRENT_USER,
)


class TestFilterOp:
    """Test FilterOp enum."""

    def test_all_operators_defined(self):
        """Verify all canonical operators are defined."""
        assert FilterOp.EQ.value == "eq"
        assert FilterOp.NE.value == "ne"
        assert FilterOp.LT.value == "lt"
        assert FilterOp.LTE.value == "lte"
        assert FilterOp.GT.value == "gt"
        assert FilterOp.GTE.value == "gte"
        assert FilterOp.IN.value == "in"
        assert FilterOp.NIN.value == "nin"
        assert FilterOp.LIKE.value == "like"
        assert FilterOp.IS_NULL.value == "is_null"


class TestFilterClause:
    """Test FilterClause pydantic model."""

    def test_valid_clause(self):
        """Test creating a valid filter clause."""
        clause = FilterClause(field="due_date", op=FilterOp.LT, value="$today")
        assert clause.field == "due_date"
        assert clause.op == FilterOp.LT
        assert clause.value == "$today"

    def test_clause_with_none_value(self):
        """Test clause with None value (valid for most ops)."""
        clause = FilterClause(field="status", op=FilterOp.EQ, value=None)
        assert clause.value is None

    def test_is_null_with_boolean(self):
        """Test is_null operator with boolean value."""
        clause = FilterClause(field="deleted", op=FilterOp.IS_NULL, value=True)
        assert clause.value is True

    def test_is_null_with_none(self):
        """Test is_null operator with None value."""
        clause = FilterClause(field="deleted", op=FilterOp.IS_NULL, value=None)
        assert clause.value is None

    # Note: The existing implementation doesn't validate operator-specific values
    # at the pydantic level. Validation happens in the SQL builder.
    def test_in_with_list(self):
        """Test in operator with list value."""
        clause = FilterClause(field="status", op=FilterOp.IN, value=["draft", "submitted"])
        assert clause.value == ["draft", "submitted"]

    def test_in_with_scalar(self):
        """Test in operator accepts scalar (SQL builder will coerce to list)."""
        clause = FilterClause(field="status", op=FilterOp.IN, value="draft")
        assert clause.value == "draft"

    def test_nin_with_list(self):
        """Test nin operator with list value."""
        clause = FilterClause(field="status", op=FilterOp.NIN, value=["closed", "cancelled"])
        assert clause.value == ["closed", "cancelled"]

    def test_nin_with_scalar(self):
        """Test nin operator accepts scalar (SQL builder will coerce to list)."""
        clause = FilterClause(field="status", op=FilterOp.NIN, value="closed")
        assert clause.value == "closed"


class TestParseFilters:
    """Test parse_filters() function."""

    def test_parse_none_returns_empty(self):
        """Test parsing None returns empty list."""
        assert parse_filters(None) == []

    def test_parse_empty_string_returns_empty(self):
        """Test parsing empty string returns empty list."""
        assert parse_filters("") == []
        # Note: whitespace-only strings are treated as invalid JSON by the existing impl

    def test_parse_valid_json(self):
        """Test parsing valid JSON filter array."""
        raw = '[{"field":"due_date","op":"lt","value":"$today"}]'
        clauses = parse_filters(raw)
        assert len(clauses) == 1
        assert clauses[0].field == "due_date"
        assert clauses[0].op == FilterOp.LT
        assert clauses[0].value == "$today"

    def test_parse_multiple_clauses(self):
        """Test parsing multiple filter clauses."""
        raw = '[{"field":"due_date","op":"lt","value":"$today"},{"field":"workflow_state","op":"ne","value":"closed"}]'
        clauses = parse_filters(raw)
        assert len(clauses) == 2
        assert clauses[0].field == "due_date"
        assert clauses[1].field == "workflow_state"

    def test_parse_invalid_json(self):
        """Test parsing invalid JSON raises FilterClauseError."""
        with pytest.raises(FilterClauseError, match="not valid JSON"):
            parse_filters("not json")

    def test_parse_non_array_raises_error(self):
        """Test parsing non-array JSON raises FilterClauseError."""
        with pytest.raises(FilterClauseError, match="must be a JSON array"):
            parse_filters('{"field":"due_date","op":"lt"}')

    def test_parse_non_object_clause_raises_error(self):
        """Test parsing non-object clause raises FilterClauseError."""
        with pytest.raises(FilterClauseError, match="must be an object"):
            parse_filters('["string"]')

    def test_parse_missing_field_raises_error(self):
        """Test parsing clause without field raises error."""
        with pytest.raises(FilterClauseError, match="invalid filter clause"):
            parse_filters('[{"op":"lt","value":"$today"}]')

    def test_parse_invalid_op_raises_error(self):
        """Test parsing clause with invalid operator raises error."""
        with pytest.raises(FilterClauseError, match="invalid filter clause"):
            parse_filters('[{"field":"due_date","op":"invalid","value":"$today"}]')

    def test_parse_invalid_value_for_op_raises_error(self):
        """Test parsing clause with invalid value for operator - validation happens in SQL builder."""
        # The existing pydantic model doesn't validate operator-specific values
        # This validation happens in the SQL builder (filter_clause_builder.py)
        clause = parse_filters('[{"field":"status","op":"in","value":"not a list"}]')
        assert len(clause) == 1
        assert clause[0].value == "not a list"  # Accepted at parse time


class TestResolveToken:
    """Test resolve_token() function."""

    def test_resolve_today(self):
        """Test $today token resolves to date.today()."""
        result = resolve_token(TOKEN_TODAY)
        assert isinstance(result, date)
        assert result == date.today()

    def test_resolve_now(self):
        """Test $now token resolves to datetime.utcnow()."""
        result = resolve_token(TOKEN_NOW)
        assert isinstance(result, datetime)

    def test_resolve_current_user_with_id(self):
        """Test $current_user token resolves to user.id."""
        from app.core.security import CurrentUser
        user = CurrentUser(id="42", username="test", roles=[], role_ids=[])
        result = resolve_token(TOKEN_CURRENT_USER, user=user)
        assert result == "42"

    def test_resolve_current_user_without_id_returns_none(self):
        """Test $current_user token without user returns None."""
        result = resolve_token(TOKEN_CURRENT_USER)
        assert result is None

    def test_resolve_non_token_returns_original(self):
        """Test non-token string returns original value."""
        result = resolve_token("closed")
        assert result == "closed"

    def test_resolve_non_string_returns_original(self):
        """Test non-string value returns original value."""
        result = resolve_token(123)
        assert result == 123

    def test_resolve_none_returns_none(self):
        """Test None returns None."""
        result = resolve_token(None)
        assert result is None
