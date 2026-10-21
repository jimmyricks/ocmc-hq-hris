"""Tests for model-derived entity field metadata.

Fields in entity JSON are an exposure whitelist over SQLAlchemy models; the
schema (type, required, link target, unique) is derived from the mapped model,
not from JSON declarations.
"""

from sqlalchemy import inspect as sa_inspect

from app.meta.model_introspection import _model_columns, resolve_model
from app.meta.registry import MetaRegistry


def test_every_declared_field_maps_to_a_model_column():
    """No phantom fields: every field declared in entity JSON must exist on the model."""
    problems = []
    for meta in MetaRegistry.list_all():
        model = resolve_model(meta.name, meta.table_name)
        assert model is not None, f"{meta.name} has no registered model"
        columns = _model_columns(model)
        for field in meta.fields:
            if field.name not in columns:
                problems.append(f"{meta.name}.{field.name}")
    assert not problems, f"fields without model columns: {problems}"


def test_undeclared_model_columns_are_not_exposed():
    """Columns absent from the JSON whitelist stay hidden from generic CRUD."""
    exposed = {f.name for f in MetaRegistry.get("user").fields}
    assert "hashed_password" not in exposed


def test_foreign_key_field_derives_link_type():
    meta = MetaRegistry.get("task_type")
    field = next(f for f in meta.fields if f.name == "workspace_id")
    assert field.field_type == "link"
    assert field.link_entity == "workspace"


def test_composite_foreign_keys_do_not_override_scalar_link_targets():
    meta = MetaRegistry.get("task")
    field = next(f for f in meta.fields if f.name == "workspace_id")
    assert field.link_entity == "workspace"


def test_non_nullable_field_with_default_remains_required_in_metadata():
    meta = MetaRegistry.get("project")
    field = next(f for f in meta.fields if f.name == "is_continuous")
    assert field.required is True
    assert field.default is False


def test_json_ui_hints_override_derived_type():
    """A declared select/currency refinement keeps its UI type."""
    meta = MetaRegistry.get("task_type")
    by_name = {f.name: f for f in meta.fields}
    assert by_name["unit"].field_type == "select"
    assert [o["value"] for o in by_name["unit"].options] == [
        "per_task",
        "per_hour",
        "per_deliverable",
        "per_unit",
    ]
    assert by_name["unit_rate"].field_type == "currency"


def test_labels_and_list_view_hints_come_from_json():
    meta = MetaRegistry.get("task_type")
    by_name = {f.name: f for f in meta.fields}
    assert by_name["name"].label == "Task Type Name"
    assert by_name["name"].in_list_view is True
    assert by_name["description"].in_list_view is False


def test_relationship_columns_are_skipped():
    """ORM relationships (non-column attributes) never appear as fields."""
    for meta in MetaRegistry.list_all():
        model = resolve_model(meta.name, meta.table_name)
        mapper = sa_inspect(model)
        relationship_keys = set(mapper.relationships.keys())
        field_names = {f.name for f in meta.fields}
        assert not (relationship_keys & field_names), (
            f"{meta.name} exposes relationships as fields"
        )
