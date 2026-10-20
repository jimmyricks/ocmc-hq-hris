"""
Reports Registry
================

Holds the canonical REPORTS map and the report rendering/data functions.

Adding a new report:
    1. Create a data fetcher (async def fetch_<name>(filters, db) -> dict)
    2. Create a Jinja2 template in templates/reports/<name>.html
    3. Register it in definitions.py:
           REPORTS["<name>"] = {
               "title": "...",
               "description": "...",
               "data_fetcher": fetch_<name>,
               "template": "<name>.html",
               "filters": [...],
           }

In the barebones backend the registry is empty.
"""
from typing import Optional

REPORTS: dict[str, dict] = {}


async def get_report_data(report_key: str, filters: Optional[dict], db) -> dict:
    """Fetch data for a registered report."""
    cfg = REPORTS.get(report_key)
    if not cfg:
        return {}
    fetcher = cfg.get("data_fetcher")
    if not fetcher:
        return {}
    return await fetcher(filters or {}, db)


def render_report_html(report_key: str, data: dict, filters: Optional[dict]) -> str:
    """Render a report's HTML preview using its configured Jinja2 template."""
    return ""
