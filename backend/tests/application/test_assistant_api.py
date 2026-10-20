import json

import pytest

from app.api.features.assistant import AssistantChatRequest, assistant_chat
from app.core.security import CurrentUser


@pytest.mark.asyncio
async def test_chat_contract_is_explicitly_unavailable_until_provider_is_wired():
    response = await assistant_chat(
        AssistantChatRequest(message="List my open tasks", conversation_id="chat-1"),
        CurrentUser(id="user-1", username="employee", roles=["User"]),
    )

    assert response.status_code == 503
    payload = json.loads(response.body)
    assert payload["code"] == "assistant_not_configured"
    assert "RAG" in payload["message"] or "retrieval" in payload["message"]
