"""
Modules package placeholder.

This package previously housed business-domain modules (e.g. asset management,
maintenance, purchasing).  It is now kept as a structural placeholder so the
core module loader continues to work; new modules can be added here later.

Each module should follow the layout:
    {module_name}/
        __init__.py
        hooks.py
        models/
            __init__.py
            {entity}.py
        entities/
            {entity}.json
"""
from pathlib import Path
from typing import List


def get_installed_modules() -> List[str]:
    """Get list of installed module names."""
    modules_dir = Path(__file__).parent
    modules = []
    for item in modules_dir.iterdir():
        if item.is_dir() and not item.name.startswith("_") and (item / "__init__.py").exists():
            modules.append(item.name)
    return sorted(modules)


def get_module_path(module_name: str) -> Path:
    """Get the path to a module directory."""
    return Path(__file__).parent / module_name
