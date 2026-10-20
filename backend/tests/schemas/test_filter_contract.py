"""
Filter contract unit tests (Story 0).

Covers ``parse_filters`` shape validation, operator set, and the
``resolve_token`` scaffold.
"""
from __future__ import annotations

from datetime import date, datetime

import pytest

from app.api.schemas.filter_clause import (
    FILTER_OPS,
    FilterClause,
    FilterClauseError,
    FilterOp,
    TOKEN_CURRENT_USER,
    TOKEN_NOW,
    TOKEN_TODAY,
    TOKEN_RESOLVERS,
    parse_filters,
    resolve_token,
)


class _StubUser:
    """Minimal stand-in for ``app.core.security.CurrentUser``."""

    def __init__(self, user_id: str) -> None:
        self.id = user_id


class TestParseFilters:
    def test_none_and_empty_return_empty_list(self):
        assert parse_filters(None) == []
        assert parse_filters("") == []

    def test_round_trip_valid_json(self):
        raw = '[{"field":"due_date","op":"lt","value":"$today"}]'
        result = parse_filters(raw)
        assert len(result) == 1
        assert isinstance(result[0], FilterClause)
        assert result[0].field == "due_date"
        assert result[0].op is FilterOp.LT
        assert result[0].value == "$today"

    def test_decodes_overdue_compound(self):
        raw = (
            '[{"field":"due_date","op":"lt","value":"$today"},'
            '{"field":"workflow_state","op":"ne","value":"closed"}]'
        )
        result = parse_filters(raw)
        assert len(result) == 2
        assert [c.field for c in result] == ["due_date", "workflow_state"]
        assert [c.op for c in result] == [FilterOp.LT, FilterOp.NE]

    def test_lowercases_operator(self):
        result = parse_filters('[{"field":"x","op":"LT","value":1}]')
        assert result[0].op is FilterOp.LT

    def test_rejects_non_string(self):
        with pytest.raises(FilterClauseError):
            parse_filters(123)  # type: ignore[arg-type]

    def test_rejects_bad_json(self):
        with pytest.raises(FilterClauseError):
            parse_filters("[not json")

    def test_rejects_non_array(self):
        with pytest.raises(FilterClauseError):
            parse_filters('{"field":"x","op":"eq","value":1}')

    def test_rejects_unknown_op(self):
        with pytest.raises(FilterClauseError):
            parse_filters('[{"field":"x","op":"between","value":1}]')

    def test_rejects_non_object_clause(self):
        with pytest.raises(FilterClauseError):
            parse_filters('[{"field":"x","op":"eq","value":1}, "garbage"]')

    def test_rejects_missing_field(self):
        with pytest.raises(FilterClauseError):
            parse_filters('[{"op":"eq","value":1}]')

    def test_rejects_empty_field(self):
        with pytest.raises(FilterClauseError):
            parse_filters('[{"field":"   ","op":"eq","value":1}]')

    def test_rejects_non_list_payload(self):
        with pytest.raises(FilterClauseError):
            parse_filters('"just a string"')

    def test_null_payload_returns_empty(self):
        assert parse_filters("null") == []


class TestFilterOpEnum:
    def test_contains_all_expected_values(self):
        assert set(FILTER_OPS) == {
            "eq",
            "ne",
            "lt",
            "lte",
            "gt",
            "gte",
            "in",
            "nin",
            "like",
            "is_null",
        }

    def test_token_constants_present(self):
        assert TOKEN_TODAY == "$today"
        assert TOKEN_NOW == "$now"
        assert TOKEN_CURRENT_USER == "$current_user"


class TestResolveToken:
    def test_today_token(self):
        resolved = resolve_token(TOKEN_TODAY)
        assert resolved == date.today()
        assert isinstance(resolved, date)

    def test_now_token(self):
        resolved = resolve_token(TOKEN_NOW)
        assert isinstance(resolved, datetime)

    def test_current_user_token(self):
        user = _StubUser("user-42")
        assert resolve_token(TOKEN_CURRENT_USER, user=user) == "user-42"

    def test_current_user_token_no_user(self):
        assert resolve_token(TOKEN_CURRENT_USER) is None

    def test_passes_through_non_token_string(self):
        assert resolve_token("closed") == "closed"

    def test_passes_through_non_string(self):
        assert resolve_token(42) == 42
        assert resolve_token([1, 2, 3]) == [1, 2, 3]

    def test_unknown_token_raises(self):
        with pytest.raises(FilterClauseError):
            resolve_token("$unknown")

    def test_resolves_tokens_in_list(self):
        # lists are resolved recursively
        today = resolve_token(TOKEN_TODAY)
        resolved = resolve_token([TOKEN_TODAY, "closed"])
        assert resolved[0] == today
        assert resolved[1] == "closed"

    def test_token_resolvers_map_is_complete(self):
        # If a new token is added, the contract should be reflected here.
        for token in (TOKEN_TODAY, TOKEN_NOW, TOKEN_CURRENT_USER):
            assert token in TOKEN_RESOLVERS
