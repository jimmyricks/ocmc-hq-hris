"""Authenticated chat contract for the self-hosted workspace assistant."""
from __future__ import annotations

from typing import Literal, Optional

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.security import CurrentUser, require_authenticated_user

router = APIRouter(prefix="/assistant", tags=["assistant"])


class AssistantHistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class AssistantChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    conversation_id: Optional[str] = Field(default=None, max_length=128)
    history: list[AssistantHistoryMessage] = Field(default_factory=list, max_length=20)


@router.get("/status")
async def assistant_status(
    current_user: CurrentUser = Depends(require_authenticated_user),
):
    del current_user
    provider_configured = bool(
        settings.ASSISTANT_ENABLED
        and settings.ASSISTANT_API_BASE_URL
        and settings.ASSISTANT_MODEL
    )
    return {
        "status": "success",
        "data": {
            "ready": False,
            "provider_configured": provider_configured,
            "tools_configured": False,
            "message": "The assistant provider, retrieval, and tool handlers are not connected yet.",
        },
    }


@router.post("/chat")
async def assistant_chat(
    payload: AssistantChatRequest,
    current_user: CurrentUser = Depends(require_authenticated_user),
):
    # Identity and permissions must come from the authenticated request, never chat input.
    del current_user
    if not payload.message.strip():
        return JSONResponse(
            status_code=422,
            content={"status": "error", "message": "Message cannot be empty."},
        )

    # The response contract is stable for the frontend; add the local model,
    # RAG retrieval, and permission-checked tool runner here when configured.
    return JSONResponse(
        status_code=503,
        content={
            "status": "error",
            "code": "assistant_not_configured",
            "message": (
                "The assistant API is not connected yet. Configure a provider "
                "and enable retrieval and tools before sending workspace queries."
            ),
            "conversation_id": payload.conversation_id,
        },
    )
