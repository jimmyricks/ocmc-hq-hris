"""Assignment email delivery, isolated from the task transaction."""
from __future__ import annotations

import logging

from app.application.email_notifications.dispatcher import (
    EmailNotificationDispatcher,
)
from app.core.config import settings
from app.core.database import async_session_maker
from app.core.serialization import record_to_dict
from app.infrastructure.email.notification_factory import (
    build_email_notification_dispatcher,
)
from app.modules.project_tasks.models import Task
from app.core.framework.models.auth import User

logger = logging.getLogger(__name__)


async def send_task_assignment_email(task_id: str, user_id: str) -> None:
    """Email the assignee after the task assignment has committed."""
    try:
        async with async_session_maker() as db:
            task = await db.get(Task, task_id)
            user = await db.get(User, user_id)
            if not task or not user or not user.email or not user.is_active:
                return

            dispatcher: EmailNotificationDispatcher = (
                build_email_notification_dispatcher(db)
            )
            base_url = (settings.PUBLIC_APP_URL or "").rstrip("/")
            action_url = f"{base_url}/project/{task.project_id}" if base_url else None
            result = await dispatcher.notify_recipients(
                "task",
                "task_assigned",
                record_to_dict(task),
                [user.email],
                action_url=action_url,
                custom_message=(
                    f"You've been assigned to task {task.title}. "
                    "Open your project workspace to review the details."
                ),
            )
            if not result.success:
                logger.warning(
                    "Task assignment email failed for task=%s user=%s: %s",
                    task_id,
                    user_id,
                    result.message,
                )
    except Exception:
        logger.warning(
            "Task assignment email delivery failed for task=%s user=%s",
            task_id,
            user_id,
            exc_info=True,
        )
