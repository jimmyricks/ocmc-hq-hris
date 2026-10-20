"""
Meta Layer: Model Introspection
===============================
Derives entity field schema from SQLAlchemy models.

SQLAlchemy models (migrated by Alembic) are the single source of truth for
schema. Entity JSON files contribute only UI/behaviour hints — labels,
list-view flags, select options, required overrides, and field order — plus
the exposure whitelist: a model column that is not declared in the JSON
``fields`` list is never exposed through generic CRUD.

Merge rules for each JSON-declared field:
  - The field must map to a mapped column attribute on the model, otherwise
    it is dropped with a warning.
  - ``field_type`` is derived from the column type (or ``link`` when the
    column carries a ForeignKey). The JSON's ``field_type`` is kept only
    when it is a compatible UI refinement (e.g. a ``String`` column may be
    rendered as ``select``, ``email``, ``attach``...).
  - ``link_entity`` is resolved from the FK target table; when the target
    table has no registered entity the JSON's ``link_entity`` is kept
    (soft-link pattern: an id stored in a plain String column).
  - ``nullable`` = the column's nullability (authoritative).
  - ``required`` = ``not nullable OR json.required`` — JSON can only
    strengthen, never weaken a database constraint.
  - ``unique`` = the column's ``unique`` flag.
  - ``default`` = JSON value (it is a form default, not a column default).
"""
from __future__ import annotations

import logging
from typing import Any, Optional

import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.orm import ColumnProperty

from app.core.database import Base
from app.meta.registry import FieldMeta

logger = logging.getLogger(__name__)

# Attributes inherited from BaseModel / managed by the server. They are never
# treated as entity fields even if a JSON file declares them.
SYSTEM_FIELDS = frozenset(
    {"id", "created_by", "created_at", "last_modified_by", "updated_at", "workflow_state", "row_no"}
)

# field_type values allowed as UI refinements of each derived base type.
_UI_REFINEMENTS: dict[str, frozenset[str]] = {
    "string": frozenset(
        {
            "string", "data", "text", "textarea", "rich_text", "email", "phone",
            "url", "password", "attach", "image", "file", "attach_image",
            "select", "multiselect", "time", "query_link", "link",
        }
    ),
    "text": frozenset({"text", "textarea", "rich_text", "data", "string"}),
    "int": frozenset({"int", "integer"}),
    "float": frozenset({"float", "number", "currency", "percent"}),
    "boolean": frozenset({"boolean", "bool"}),
    "date": frozenset({"date"}),
    "datetime": frozenset({"datetime"}),
    "time": frozenset({"time"}),
    "link": frozenset({"link", "parent_child_link"}),
}

# Field types that do not map to a single column.
_NON_COLUMN_TYPES = frozenset({"date_range"})

# Keys copied verbatim from the JSON field entry. Schema attributes handled
# explicitly in derive_fields (label, required, readonly, hidden, unique,
# link_entity, nullable, field_type) are intentionally absent.
_HINT_KEYS = (
    "in_list_view",
    "child_entity", "parent_entity", "child_parent_fk_field", "query",
    "default", "options", "show_when", "editable_when", "required_when",
    "display_depends_on", "mandatory_depends_on", "fetch_from", "filter_by",
    "column_group", "list_view_depends_on", "copy_from_parent",
    "readonly_depends_on", "in_options_description", "placeholder",
    "description", "computed_from", "link_filter", "search_fields",
)


def resolve_model(entity_name: str, table_name: str) -> Optional[type]:
    """Resolve the SQLAlchemy model class for an entity.

    Lookup order: models registered under the entity name, then a scan of
    ``Base.registry.mappers`` by ``__tablename__``.
    """
    from app.infrastructure.database.repositories.entity_repository import (
        _REGISTERED_MODELS,
    )

    model = _REGISTERED_MODELS.get(entity_name)
    if model is not None:
        return model

    for mapper in Base.registry.mappers:
        cls = mapper.class_
        table = getattr(cls, "__tablename__", None)
        if table in (table_name, entity_name):
            return cls
    return None


def build_table_entity_map(entity_defs: list[dict[str, Any]]) -> dict[str, str]:
    """Build a table_name -> entity_name map from entity JSON definitions.

    *entity_defs* only needs ``name`` and ``table_name`` keys; a cheap first
    pass over the JSON files supplies them before fields are derived.
    """
    mapping: dict[str, str] = {}
    for definition in entity_defs:
        name = definition.get("name")
        if not name:
            continue
        table_name = definition.get("table_name") or name
        mapping[table_name] = name
    return mapping


def _column_base_type(column: sa.Column) -> str:
    """Map a SQLAlchemy column type to the canonical field_type."""
    if column.foreign_keys:
        return "link"
    col_type = column.type
    if isinstance(col_type, sa.Boolean):
        return "boolean"
    if isinstance(col_type, sa.Integer):
        return "int"
    if isinstance(col_type, (sa.Float, sa.Numeric)):
        return "float"
    if isinstance(col_type, sa.DateTime):
        return "datetime"
    if isinstance(col_type, sa.Date):
        return "date"
    if isinstance(col_type, sa.Time):
        return "time"
    if isinstance(col_type, sa.Text):
        return "text"
    return "string"


def _fk_link_entity(
    column: sa.Column, table_to_entity: dict[str, str]
) -> Optional[str]:
    """Return the entity name for a column's FK target table, if known."""
    for fk in column.foreign_keys:
        entity = table_to_entity.get(fk.column.table.name)
        if entity:
            return entity
    return None


def _model_columns(model: type) -> dict[str, sa.Column]:
    """Return ``{attribute_name: Column}`` for a mapped model."""
    columns: dict[str, sa.Column] = {}
    for prop in sa_inspect(model).attrs:
        if not isinstance(prop, ColumnProperty):
            continue
        if not prop.columns:
            continue
        columns[prop.key] = prop.columns[0]
    return columns


def _apply_hints(field: FieldMeta, field_data: dict[str, Any]) -> None:
    """Overlay JSON hint keys onto a derived FieldMeta."""
    for key in _HINT_KEYS:
        if key in field_data:
            setattr(field, key, field_data[key])


def derive_fields(
    entity_name: str,
    table_name: str,
    json_fields: list[dict[str, Any]],
    table_to_entity: dict[str, str],
    *,
    model: Optional[type] = None,
) -> tuple[list[FieldMeta], list[str]]:
    """Merge JSON field declarations with model-derived schema.

    Returns ``(fields, warnings)``. When no model can be resolved the JSON
    declarations are returned as-is (with a warning) so behaviour matches the
    previous loader instead of silently emptying the entity.
    """
    warnings: list[str] = []

    if model is None:
        model = resolve_model(entity_name, table_name)

    if model is None:
        warnings.append(
            f"Entity '{entity_name}': no SQLAlchemy model found for table "
            f"'{table_name}' — using JSON field declarations"
        )
        return _json_declared_fields(json_fields), warnings

    columns = _model_columns(model)

    fields: list[FieldMeta] = []
    for field_data in json_fields:
        name = field_data.get("name")
        if not name:
            continue
        if name in SYSTEM_FIELDS:
            continue

        column = columns.get(name)

        # Composite date_range: backed by <name>_start / <name>_end columns.
        if column is None and field_data.get("field_type") in _NON_COLUMN_TYPES:
            start_col = columns.get(f"{name}_start")
            if start_col is not None and columns.get(f"{name}_end") is not None:
                column = start_col
                field_data = {**field_data, "field_type": "date_range"}

        if column is None:
            warnings.append(
                f"Entity '{entity_name}': field '{name}' has no column on "
                f"{model.__name__} — dropped from metadata"
            )
            continue

        base_type = _column_base_type(column)
        json_type = field_data.get("field_type")
        if json_type and json_type != base_type:
            allowed = _UI_REFINEMENTS.get(base_type, frozenset({base_type}))
            if json_type in allowed:
                base_type = json_type
            else:
                warnings.append(
                    f"Entity '{entity_name}': field '{name}' declared as "
                    f"'{json_type}' but column is '{base_type}' — using model type"
                )

        link_entity = field_data.get("link_entity")
        child_entity = field_data.get("child_entity")
        if base_type in ("link", "parent_child_link"):
            derived_link = _fk_link_entity(column, table_to_entity)
            if derived_link:
                target = "child_entity" if base_type == "parent_child_link" else "link_entity"
                declared = child_entity if base_type == "parent_child_link" else link_entity
                if declared and declared != derived_link:
                    warnings.append(
                        f"Entity '{entity_name}': field '{name}' {target} "
                        f"'{declared}' does not match FK target "
                        f"'{derived_link}' — using model"
                    )
                if base_type == "parent_child_link":
                    child_entity = derived_link
                else:
                    link_entity = derived_link
            # else: keep JSON value (soft link, or target has no entity)

        field = FieldMeta(
            name=name,
            label=field_data.get("label", name),
            field_type=base_type,
            required=(not column.nullable) or bool(field_data.get("required")),
            readonly=bool(field_data.get("readonly", False)),
            hidden=bool(field_data.get("hidden", False)),
            unique=bool(column.unique),
            link_entity=link_entity,
            child_entity=child_entity,
            nullable=column.nullable,
        )
        _apply_hints(field, field_data)
        fields.append(field)

    unexposed = sorted(
        key for key in columns if key not in SYSTEM_FIELDS and key not in {f.name for f in fields}
    )
    if unexposed:
        logger.debug(
            "Entity '%s': %d model column(s) not exposed: %s",
            entity_name,
            len(unexposed),
            ", ".join(unexposed),
        )

    return fields, warnings


def _json_declared_fields(json_fields: list[dict[str, Any]]) -> list[FieldMeta]:
    """Build FieldMeta purely from JSON (no model available)."""
    fields: list[FieldMeta] = []
    for field_data in json_fields:
        name = field_data.get("name")
        if not name or name in SYSTEM_FIELDS:
            continue
        field = FieldMeta(
            name=name,
            label=field_data.get("label", name),
            field_type=field_data.get("field_type", "string"),
            required=bool(field_data.get("required", False)),
            readonly=bool(field_data.get("readonly", False)),
            hidden=bool(field_data.get("hidden", False)),
            unique=bool(field_data.get("unique", False)),
            link_entity=field_data.get("link_entity"),
            nullable=field_data.get("nullable", True),
        )
        _apply_hints(field, field_data)
        fields.append(field)
    return fields


def fields_fingerprint(fields: list[FieldMeta]) -> str:
    """Stable fingerprint of derived schema attributes for cache keys."""
    return repr(
        [
            (f.name, f.field_type, f.required, f.nullable, f.unique, f.link_entity)
            for f in fields
        ]
    )
