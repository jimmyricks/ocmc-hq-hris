"""
Domain Constants: Field Types

Source of truth for all field types supported by the system.
This ensures consistency across backend validation, generation, and frontend UI.
"""

from enum import Enum
from typing import List, Dict, Any


class FieldType(str, Enum):
    """Canonical and alias field type strings shared with the frontend."""

    STRING = "string"
    DATA = "data"
    TEXT = "text"
    TEXTAREA = "textarea"
    RICH_TEXT = "rich_text"
    INTEGER = "integer"
    INT = "int"
    FLOAT = "float"
    NUMBER = "number"
    CURRENCY = "currency"
    PERCENT = "percent"
    BOOLEAN = "boolean"
    BOOL = "bool"
    DATE = "date"
    DATETIME = "datetime"
    TIME = "time"
    SELECT = "select"
    MULTISELECT = "multiselect"
    LINK = "link"
    QUERY_LINK = "query_link"
    PARENT_CHILD_LINK = "parent_child_link"
    EMAIL = "email"
    PHONE = "phone"
    URL = "url"
    PASSWORD = "password"
    ATTACH = "attach"
    IMAGE = "image"
    FILE = "file"
    ATTACH_IMAGE = "attach_image"
    DATE_RANGE = "date_range"


# All valid field types supported by the system
VALID_FIELD_TYPES: List[str] = [ft.value for ft in FieldType]

# Alias -> canonical type used by the Svelte renderer and other consumers
# that expect a normalized set.
FIELD_TYPE_NORMALIZE: Dict[str, str] = {
    FieldType.BOOL.value: FieldType.BOOLEAN.value,
    FieldType.NUMBER.value: FieldType.FLOAT.value,
    FieldType.INTEGER.value: FieldType.INT.value,
    FieldType.TEXTAREA.value: FieldType.TEXT.value,
    FieldType.RICH_TEXT.value: FieldType.TEXT.value,
    FieldType.DATA.value: FieldType.STRING.value,
}

# Detailed field type mappings for code generation
FIELD_TYPE_MAPPINGS: Dict[str, Dict[str, Any]] = {
    "string": {"py_type": "str", "sa_type": "String(255)", "imports": ["String"]},
    "data": {"py_type": "str", "sa_type": "String(255)", "imports": ["String"]},
    "text": {"py_type": "str", "sa_type": "Text", "imports": ["Text"]},
    "textarea": {"py_type": "str", "sa_type": "Text", "imports": ["Text"]},
    "rich_text": {"py_type": "str", "sa_type": "Text", "imports": ["Text"]},
    "int": {"py_type": "int", "sa_type": "Integer", "imports": ["Integer"]},
    "integer": {"py_type": "int", "sa_type": "Integer", "imports": ["Integer"]},
    "float": {"py_type": "float", "sa_type": "Float", "imports": ["Float"]},
    "number": {"py_type": "float", "sa_type": "Float", "imports": ["Float"]},
    "currency": {"py_type": "float", "sa_type": "Numeric(12, 2)", "imports": ["Numeric"]},
    "percent": {"py_type": "float", "sa_type": "Numeric(5, 2)", "imports": ["Numeric"]},
    "boolean": {"py_type": "bool", "sa_type": "Boolean", "imports": ["Boolean"]},
    "bool": {"py_type": "bool", "sa_type": "Boolean", "imports": ["Boolean"]},
    "date": {"py_type": "date", "sa_type": "Date", "imports": ["Date"]},
    "datetime": {"py_type": "datetime", "sa_type": "DateTime", "imports": ["DateTime"]},
    "time": {"py_type": "str", "sa_type": "String(50)", "imports": ["String"]},
    "select": {"py_type": "str", "sa_type": "String(100)", "imports": ["String"]},
    "multiselect": {"py_type": "str", "sa_type": "String(255)", "imports": ["String"]},
    "link": {"py_type": "str", "sa_type": "String(50)", "imports": ["String", "ForeignKey"]},
    "query_link": {"py_type": "str", "sa_type": "String(50)", "imports": ["String"]},
    "email": {"py_type": "str", "sa_type": "String(255)", "imports": ["String"]},
    "phone": {"py_type": "str", "sa_type": "String(50)", "imports": ["String"]},
    "url": {"py_type": "str", "sa_type": "String(500)", "imports": ["String"]},
    "password": {"py_type": "str", "sa_type": "String(255)", "imports": ["String"]},
    "attach": {"py_type": "str", "sa_type": "String(500)", "imports": ["String"]},
    "image": {"py_type": "str", "sa_type": "String(500)", "imports": ["String"]},
    "file": {"py_type": "str", "sa_type": "String(500)", "imports": ["String"]},
    "attach_image": {"py_type": "str", "sa_type": "String(500)", "imports": ["String"]},
    "parent_child_link": {"py_type": "str", "sa_type": "String(50)", "imports": ["String", "ForeignKey"]},
    "date_range": {"py_type": "date", "sa_type": "Date", "imports": ["Date"], "composite": True},
}

# Legacy tuple format for backward compatibility (simple Python type, SQLAlchemy type)
FIELD_TYPE_MAP: Dict[str, tuple] = {
    "string": ("str", "String(255)"),
    "data": ("str", "String(255)"),
    "text": ("str", "Text"),
    "textarea": ("str", "Text"),
    "rich_text": ("str", "Text"),
    "int": ("int", "Integer"),
    "integer": ("int", "Integer"),
    "float": ("float", "Numeric(10, 2)"),
    "number": ("float", "Numeric(10, 2)"),
    "boolean": ("bool", "Boolean"),
    "bool": ("bool", "Boolean"),
    "date": ("datetime", "Date"),
    "datetime": ("datetime", "DateTime"),
    "time": ("str", "String(50)"),
    "select": ("str", "String(100)"),
    "multiselect": ("str", "String(255)"),
    "attach": ("str", "String(500)"),
    "image": ("str", "String(500)"),
    "file": ("str", "String(500)"),
    "attach_image": ("str", "String(500)"),
    "email": ("str", "String(255)"),
    "phone": ("str", "String(50)"),
    "url": ("str", "String(500)"),
    "password": ("str", "String(255)"),
    "query_link": ("str", "String(50)"),
    "link": ("str", "String(50)"),
    "parent_child_link": ("str", "String(50)"),
    "currency": ("float", "Numeric(12, 2)"),
    "percent": ("float", "Numeric(5, 2)"),
    "date_range": ("date", "Date"),
}

# Field type descriptions for UI
FIELD_TYPE_DESCRIPTIONS = {
    "string": "Text field",
    "data": "Short text field",
    "text": "Long text field",
    "textarea": "Multi-line text field",
    "rich_text": "Rich text field",
    "int": "Whole number",
    "integer": "Whole number",
    "float": "Decimal number",
    "number": "Decimal number",
    "boolean": "True/False",
    "bool": "True/False",
    "date": "Date only",
    "datetime": "Date and time",
    "time": "Time only",
    "select": "Dropdown selection",
    "multiselect": "Multi-select dropdown",
    "link": "Foreign key to another entity",
    "query_link": "Query-based link",
    "parent_child_link": "Parent-child relationship",
    "email": "Email address",
    "phone": "Phone number",
    "url": "URL",
    "password": "Password",
    "attach": "File attachment",
    "image": "Image file",
    "file": "File upload",
    "attach_image": "Image attachment",
    "currency": "Currency value",
    "percent": "Percentage",
    "date_range": "Date range (start and end)",
}
