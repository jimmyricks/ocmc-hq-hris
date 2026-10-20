---
title: OCMC Workspace Assistant
---

# OCMC Workspace Assistant

## Current Setup

- The authenticated chat UI is mounted throughout the private workspace.
- `POST /api/features/assistant/chat` defines the message, conversation ID, and bounded history contract.
- The endpoint intentionally returns `503 assistant_not_configured` until a provider, retrieval layer, and tool runner are connected.
- The UI keeps chat history in memory only; it does not store prompts or credentials in browser storage.

## Backend Configuration

Set these in the backend environment or a secret manager:

```env
ASSISTANT_ENABLED=true
ASSISTANT_API_BASE_URL=http://localhost:11434/v1
ASSISTANT_API_KEY=
ASSISTANT_MODEL=
```

The endpoint is OpenAI-compatible by design; a local model server may not need an API key. No provider client is currently called.

## Planned Agent Boundaries

1. Derive user identity and roles from the authenticated request, never from chat text.
2. Retrieve only project, task, and payroll data the user is allowed to read.
3. Expose a small allow-list of tools backed by existing application services.
4. Require explicit user confirmation before project, task, assignment, submission, or payroll mutations.
5. Log tool actions and outcomes without logging secrets or full private prompts.

Candidate tools: `create_project`, `create_task`, `assign_task`, `submit_work`, `query_projects`, `query_tasks`, and `calculate_payroll`.
