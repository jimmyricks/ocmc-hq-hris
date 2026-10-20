from unittest.mock import AsyncMock

import pytest

from app.application.email_notifications.dispatcher import (
    EmailNotificationDispatcher,
)


@pytest.mark.asyncio
async def test_notify_recipients_uses_explicit_assignee_address():
    email_service = AsyncMock()
    dispatcher = EmailNotificationDispatcher(email_service)
    task = {"id": "TASK-1", "title": "Prepare campaign"}

    await dispatcher.notify_recipients(
        "task",
        "task_assigned",
        task,
        ["employee@example.com"],
        action_url="https://hq.example.com/project/PRJ-1",
        custom_message="A task was assigned to you.",
    )

    email_service.send_record_notification.assert_awaited_once_with(
        entity_name="task",
        record=task,
        db=None,
        recipients=["employee@example.com"],
        event_type="task_assigned",
        custom_message="A task was assigned to you.",
        action_url="https://hq.example.com/project/PRJ-1",
    )
