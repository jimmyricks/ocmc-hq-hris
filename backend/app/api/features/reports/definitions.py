"""
Report Definitions
==================

Previously defined the EAM report catalog (work_order_summary, pr_summary,
inventory_summary, inventory_count, stock_movement, incident_summary,
maintenance_pms, budget_vs_actual).

In the barebones backend the catalog is empty.  Add report definitions here
and import them into the registry to re-enable reports.

Example:
    REPORTS: dict[str, dict] = {
        "my_report": {
            "title": "My Report",
            "description": "...",
            "category": "General",
            "icon": "i-lucide-file-text",
            "filters": [
                {"name": "from_date", "label": "From", "field_type": "date"},
                {"name": "to_date", "label": "To", "field_type": "date"},
            ],
            "data_fetcher": my_data_fetcher,
            "template": "my_report.html",
        },
    }
"""

REPORTS: dict[str, dict] = {}
