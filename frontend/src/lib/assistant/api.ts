import { apiJSON } from "$lib/api/index.js";

export type AssistantRole = "user" | "assistant";

export interface AssistantMessage {
  role: AssistantRole;
  content: string;
}

export interface AssistantChatRequest {
  message: string;
  conversation_id: string;
  history: AssistantMessage[];
}

export interface AssistantChatResponse {
  answer: string;
  conversation_id: string;
  suggested_actions?: string[];
}

export async function sendAssistantMessage(
  payload: AssistantChatRequest,
): Promise<AssistantChatResponse> {
  const response = await apiJSON("/api/features/assistant/chat", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  return response.data as AssistantChatResponse;
}
