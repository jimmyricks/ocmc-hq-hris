"""
Utils module hooks — registers scheduled jobs and startup wiring.
"""
from app.application.services.scheduling.job_registry import job_registry
from app.modules.utils.services import UtilsService


def register_hooks() -> None:
    """Register scheduled jobs for the Utils module."""
    job_registry.register(
        "scan_short_links",
        UtilsService.scan_all_short_links,
        cron_expression="daily",
        description="Re-scan active short-link destinations against the blocklist",
        enabled=True,
        replace_existing=True,
    )
