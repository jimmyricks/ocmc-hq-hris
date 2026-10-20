"""
Entity metadata loader for modular system.
Scans app/modules/{module}/entities for entity JSON files.
Workflow and RBAC are now database-driven, not loaded from JSON.
"""
import json
from pathlib import Path
from typing import Iterator, Optional
from app.meta.registry import MetaRegistry, EntityMeta, FormStateRules, TabConfig, WorkflowMeta, AttachmentConfig, ChildTableMeta, ListViewActionMeta, SectionMeta
from app.meta.model_introspection import build_table_entity_map, derive_fields


def _iter_entity_json_files() -> Iterator[tuple[Path, str]]:
    """Yield ``(json_path, module_name)`` for every entity JSON.

    Core framework entities come first (module ``core``), then module
    entities under ``app/modules/<module>/entities``. Supports both the flat
    ``entities/{entity}.json`` and legacy nested
    ``entities/{entity}/{entity}.json`` layouts.
    """
    core_entities_dir = Path(__file__).parent.parent / "core" / "framework" / "entities"
    if core_entities_dir.exists():
        yield from _iter_entity_dir(core_entities_dir, "core")

    modules_dir = Path(__file__).parent.parent / "modules"
    if modules_dir.exists():
        for module_dir in modules_dir.iterdir():
            if not module_dir.is_dir() or module_dir.name.startswith("_"):
                continue
            entities_dir = module_dir / "entities"
            if entities_dir.exists():
                yield from _iter_entity_dir(entities_dir, module_dir.name)


def _iter_entity_dir(entities_dir: Path, module_name: str) -> Iterator[tuple[Path, str]]:
    for item in entities_dir.iterdir():
        if item.name.startswith("_"):
            continue
        if item.is_file() and item.suffix == ".json":
            yield item, module_name
        elif item.is_dir():
            nested_json = item / f"{item.name}.json"
            if nested_json.exists():
                yield nested_json, module_name


def _collect_table_entity_map() -> dict[str, str]:
    """First pass: collect ``name``/``table_name`` from every entity JSON."""
    defs = []
    for json_path, _ in _iter_entity_json_files():
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        defs.append({"name": data.get("name"), "table_name": data.get("table_name")})
    return build_table_entity_map(defs)


def _load_entities_from_directory(
    entities_dir: Path,
    module_name: str,
    po_entities: list,
    po_enabled: bool,
    table_to_entity: dict[str, str],
) -> tuple[int, int]:
    """Load entities from a directory, returning (count, skipped_po)."""
    entity_count = 0
    skipped_po = 0

    for item in entities_dir.iterdir():
        if item.name.startswith("_"):
            continue

        json_file = None

        # Check for flat structure: entities/{entity}.json
        if item.is_file() and item.suffix == ".json":
            json_file = item
        # Check for nested structure: entities/{entity}/{entity}.json
        elif item.is_dir():
            nested_json = item / f"{item.name}.json"
            if nested_json.exists():
                json_file = nested_json

        if json_file and json_file.exists():
            try:
                entity_meta = load_entity_from_json(json_file, module_name, table_to_entity)
                if entity_meta:
                    # Skip PO entities when feature is disabled
                    if not po_enabled and entity_meta.name in po_entities:
                        skipped_po += 1
                        print(f"⏭️  Skipped entity (PO disabled): {entity_meta.name}")
                        continue

                    MetaRegistry.register(entity_meta)
                    entity_count += 1
                    print(f"✅ Loaded entity: {entity_meta.name} (module: {entity_meta.module})")
                    # Build and register Pydantic schemas (with hash-based disk cache)
                    try:
                        from app.meta.schema_cache import load_or_build_schemas
                        write_schema, update_schema, read_schema = load_or_build_schemas(entity_meta, json_file)
                        MetaRegistry.register_schema(
                            entity_meta.name,
                            write=write_schema,
                            update=update_schema,
                            read=read_schema,
                        )
                    except Exception as schema_err:
                        print(f"⚠️  Schema build failed for {entity_meta.name}: {schema_err}")
            except Exception as e:
                print(f"❌ Failed to load {json_file}: {e}")

    return entity_count, skipped_po


def load_all_entities():
    """Load all entity metadata from core and modular structure.

    Loading order:
    1. Core framework entities: app/core/framework/entities/{entity}.json (module='core')
    2. Module entities: app/modules/{module}/entities/{entity}.json

    Supports two structures for modules:
    1. Flat: modules/{module}/entities/{entity}.json
    2. Nested (legacy): modules/{module}/entities/{entity}/{entity}.json

    After loading, auto-registers server actions from entity JSON method paths.
    Respects feature flags (e.g. PO entities skipped when PURCHASE_ORDER_ENABLED=False).
    """
    from app.core.feature_flags import is_po_enabled, PO_ENTITIES

    entity_count = 0
    skipped_po = 0

    # First pass: build table_name -> entity_name map for FK link resolution.
    table_to_entity = _collect_table_entity_map()

    # 1. Load core framework entities first
    core_entities_dir = Path(__file__).parent.parent / "core" / "framework" / "entities"
    if core_entities_dir.exists():
        count, _ = _load_entities_from_directory(
            core_entities_dir, "core", PO_ENTITIES, is_po_enabled(), table_to_entity
        )
        entity_count += count

    # 2. Load module entities
    modules_dir = Path(__file__).parent.parent / "modules"
    if modules_dir.exists():
        for module_dir in modules_dir.iterdir():
            if not module_dir.is_dir() or module_dir.name.startswith("_"):
                continue

            entities_dir = module_dir / "entities"
            if not entities_dir.exists():
                continue

            count, skipped = _load_entities_from_directory(
                entities_dir, module_dir.name, PO_ENTITIES, is_po_enabled(), table_to_entity
            )
            entity_count += count
            skipped_po += skipped

    if skipped_po:
        print(f"⏭️  Skipped {skipped_po} PO-related entity(ies) (PURCHASE_ORDER_ENABLED=False)")
    print(f"📦 Total entities loaded: {entity_count}")

    # Post-process: PO-specific stripping is a no-op in the barebones backend
    _strip_po_references()

    # Auto-register server actions from entity JSON method paths
    _register_entity_actions()


def _parse_static_options(raw_options):
    if raw_options is None:
        return None

    # Frappe-style options are often stored as a newline-delimited string.
    if isinstance(raw_options, str):
        values = [v.strip() for v in raw_options.split("\n")]
        values = [v for v in values if v]
        return [{"value": v, "label": v} for v in values]

    # Allow list[str] or list[dict]
    if isinstance(raw_options, list):
        if not raw_options:
            return []
        if all(isinstance(v, str) for v in raw_options):
            return [{"value": v, "label": v} for v in raw_options]
        if all(isinstance(v, dict) for v in raw_options):
            normalized = []
            for item in raw_options:
                value = item.get("value") if isinstance(item, dict) else None
                label = item.get("label") if isinstance(item, dict) else None
                if value is None and label is not None:
                    value = label
                if label is None and value is not None:
                    label = str(value)
                if value is None:
                    continue
                normalized.append({"value": value, "label": label or str(value)})
            return normalized

    return None


def load_entity_from_json(
    json_path: Path,
    module_name: Optional[str] = None,
    table_to_entity: Optional[dict[str, str]] = None,
) -> Optional[EntityMeta]:
    """Load entity metadata from JSON file.

    The ``fields`` list in JSON is a UI/behaviour declaration: field order,
    labels, options and list-view flags are kept, while schema attributes
    (type, nullability, uniqueness, link target) are derived from the
    SQLAlchemy model. Fields that do not map to a model column are dropped
    with a warning.
    """
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)

        from app.meta.registry import NamingMeta, ActionMeta

        if table_to_entity is None:
            table_to_entity = _collect_table_entity_map()

        json_fields = data.get('fields', [])
        for field_data in json_fields:
            if isinstance(field_data, dict) and "options" in field_data:
                field_data["options"] = _parse_static_options(field_data.get("options"))

        entity_name = data.get('name', '')
        fields, field_warnings = derive_fields(
            entity_name,
            data.get('table_name', entity_name),
            json_fields,
            table_to_entity,
        )
        for warning in field_warnings:
            print(f"⚠️  {warning}")

        # Parse naming
        naming = None
        if 'naming' in data:
            naming_data = data['naming']
            if isinstance(naming_data, str):
                import re
                match = re.match(r'(.+)-\{(#+)\}', naming_data)
                if match:
                    prefix = match.group(1)
                    digits = len(match.group(2))
                    naming = NamingMeta(
                        enabled=True,
                        prefix=prefix,
                        digits=digits,
                        field='id'
                    )
                elif naming_data == "hash":
                    naming = NamingMeta(
                        enabled=True,
                        prefix="",
                        digits=0,
                        field='id'
                    )
            elif isinstance(naming_data, dict):
                naming = NamingMeta(
                    enabled=naming_data.get('enabled', False),
                    prefix=naming_data.get('prefix', ''),
                    digits=naming_data.get('digits', 4),
                    field=naming_data.get('field', 'id')
                )

        # Parse actions
        actions = []
        for action_data in data.get('actions', []):
            actions.append(ActionMeta(
                action=action_data['action'],
                label=action_data.get('label', action_data['action']),
                method=action_data.get('method', ''),
                confirm=action_data.get('confirm'),
                show_when=action_data.get('show_when')
            ))

        # Parse workflow config from JSON
        workflow = None
        workflow_data = data.get('workflow')
        if workflow_data and isinstance(workflow_data, dict):
            workflow = WorkflowMeta(
                enabled=workflow_data.get('enabled', False),
                show_actions=workflow_data.get('show_actions', True),
                state_field=workflow_data.get('state_field', 'workflow_state'),
                initial_state=workflow_data.get('initial_state'),
                states=workflow_data.get('states', []),
                transitions=workflow_data.get('transitions', []),
            )

        # Parse form_state rules
        form_state = None
        form_state_data = data.get('form_state')
        if form_state_data:
            tab_rules = []
            for tr in form_state_data.get('tab_rules', []):
                tab_rules.append(TabConfig(
                    entity=tr['entity'],
                    label=tr.get('label'),
                    show_when=tr.get('show_when'),
                    hide_when=tr.get('hide_when'),
                    require_data=tr.get('require_data'),
                    display_depends_on=tr.get('display_depends_on'),
                ))
            form_state = FormStateRules(
                editable_when=form_state_data.get('editable_when'),
                can_add_children_when=form_state_data.get('can_add_children_when'),
                tab_rules=tab_rules,
            )

        # Parse attachment config
        attachment_config = None
        attachment_data = data.get('attachment_config')
        if attachment_data and isinstance(attachment_data, dict):
            attachment_config = AttachmentConfig(
                allow_attachments=attachment_data.get('allow_attachments', False),
                max_attachments=attachment_data.get('max_attachments', 10),
                allowed_extensions=attachment_data.get('allowed_extensions'),
                max_file_size_mb=attachment_data.get('max_file_size_mb', 10),
            )

        # Parse children (inline child tables rendered inside the form)
        children = []
        for child_data in data.get('children', []):
            children.append(ChildTableMeta(
                entity=child_data['entity'],
                fk_field=child_data['fk_field'],
                label=child_data.get('label', child_data['entity']),
            ))

        # Parse sections (form sections for grouping fields)
        sections = []
        for section_data in data.get('sections', []):
            sections.append(SectionMeta(
                label=section_data.get('label', ''),
                fields=section_data.get('fields', []),
            ))

        field_layout = data.get('field_layout', []) or []

        # Parse list_view_actions (custom bulk actions for list view)
        list_view_actions = []
        for lva_data in data.get('list_view_actions', []):
            list_view_actions.append(ListViewActionMeta(
                action=lva_data['action'],
                label=lva_data.get('label', lva_data['action']),
                icon=lva_data.get('icon'),
                confirm=lva_data.get('confirm'),
                endpoint=lva_data.get('endpoint'),
                method=lva_data.get('method', 'POST'),
            ))

        return EntityMeta(
            name=data['name'],
            label=data.get('label', data['name']),
            module=module_name if module_name is not None else data.get('module', 'core'),
            table_name=data.get('table_name', data['name']),
            title_field=data.get('title_field', 'name'),
            owner_field=data.get('owner_field', 'created_by'),
            fields=fields,
            in_sidebar=data.get('in_sidebar', True),
            links=data.get('links', []),
            children=children,
            sections=sections,
            naming=naming,
            group=data.get('group'),
            icon=data.get('icon'),
            search_fields=data.get('search_fields'),
            actions=actions,
            form_state=form_state,
            workflow=workflow,
            attachment_config=attachment_config,
            is_tree=bool(data.get('is_tree', False)),
            tree_parent_field=data.get('tree_parent_field'),
            is_diagram=bool(data.get('is_diagram', False)),
            is_child_table=bool(data.get('is_child_table', False)),
            is_system=bool(data.get('is_system', False)),
            is_immutable=bool(data.get('is_immutable', False)),
            rbac=data.get('rbac', {}),
            prefill=data.get('prefill'),
            list_view_actions=list_view_actions,
            field_layout=field_layout,
        )
    except Exception as e:
        print(f"Error loading entity from {json_path}: {e}")
        import traceback
        traceback.print_exc()
        return None


def _strip_po_references():
    """No-op in the barebones backend."""
    pass


def reload_entity_meta(entity_name: str, json_path: Path | str) -> bool:
    """Re-load a single entity's JSON and rebuild its Pydantic schemas.

    Used after hand-editing an entity JSON in development (uvicorn reload
    does not watch ``.json`` files).
    """
    from app.meta.schema_cache import load_or_build_schemas

    entity_json_path = Path(json_path)
    entity_meta = load_entity_from_json(entity_json_path)
    if not entity_meta:
        return False
    MetaRegistry.register(entity_meta)
    write_schema, update_schema, read_schema = load_or_build_schemas(
        entity_meta, entity_json_path
    )
    MetaRegistry.register_schema(
        entity_meta.name,
        write=write_schema,
        update=update_schema,
        read=read_schema,
    )
    return True


def reload_all_entities() -> int:
    """Clear and re-load every entity JSON; returns the entity count."""
    MetaRegistry._entities.clear()
    load_all_entities()
    return len(MetaRegistry._entities)


def _register_entity_actions():
    """Auto-register server actions from entity JSON method paths.

    For each entity with actions that have a 'method' field (Python dotted path),
    dynamically import the function and register it with the ServerActionsRegistry.
    """
    from app.application.services.documents.server_actions import server_actions

    action_count = 0
    for entity_meta in MetaRegistry.list_all():
        for action in entity_meta.actions:
            if not action.method:
                continue
            try:
                server_actions.load_from_handler_path(
                    entity_meta.name, action.action, action.method
                )
                action_count += 1
            except Exception as e:
                print(f"⚠️  Failed to register action '{action.action}' for '{entity_meta.name}': {e}")

    if action_count:
        print(f"⚡ Registered {action_count} server action(s) from entity metadata")
