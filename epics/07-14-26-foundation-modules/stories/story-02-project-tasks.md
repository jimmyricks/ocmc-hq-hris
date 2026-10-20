---
date_created: 2026-07-14
date_modified: 2026-07-15
title: "US-02: Project & Tasks Module"
description: Scaffold Project, TaskType, Task, TaskAssignment, TaskSubmission, and TaskApproval
sprint: 2
points: 13
---

# US-02: Project & Tasks Module

## Status

CLOSED. `Project`, `TaskType`, `Task`, `TaskAssignment`, `TaskSubmission`, and `TaskApproval` models and JSON metadata are scaffolded in `backend/app/modules/project_tasks/`. The frontend `task-manager` (`types.ts`, `data.ts`, `task-table.svelte`, `task-modal.svelte`, `nav-projects.svelte`, `project/[id]/+page.svelte`) uses backend field names with no mapping. Verified by `tests/api/test_project_task_api_20260723.py` (8/8 pass) and `tests/epics/test_epic_workflow.py`.

## Story

As a **project manager**, I want to **create projects, define task types, assign tasks, and review submissions** so that **users can complete work and be paid for it**.

## Acceptance Criteria

- **GIVEN** a project manager, **WHEN** they create a project, **THEN** it has code, manager, status, and dates.
- **GIVEN** a project, **WHEN** a task is created, **THEN** it generates a unique `task_key` and links to `Project` and `TaskType`.
- **GIVEN** a task, **WHEN** it is assigned to a user, **THEN** a `TaskAssignment` row is created and only one is `is_active`.
- **GIVEN** a task assignment, **WHEN** a user submits work, **THEN** a `TaskSubmission` is created with `version = 1`.
- **GIVEN** a submission, **WHEN** a project manager reviews it, **THEN** a `TaskApproval` is logged and the submission status changes.
- **GIVEN** a submission rejection, **WHEN** the user resubmits, **THEN** a new `TaskSubmission` with `version + 1` and `previous_submission_id` is created.

## Models

- `Project`
- `TaskType`
- `Task`
- `TaskAssignment` (detail of `Task`)
- `TaskSubmission` (header)
- `TaskApproval` (detail of `TaskSubmission`)

## Implementation Notes

- Use `forge.py` to scaffold each entity.
- Header/detail entities are saved together with their parent.
- Workflow transitions for `Task` and `TaskSubmission` live in the entity files, not route handlers.
- DRY: reuse `AuditLog` and `Notification` from the collaboration module.
- SOLID: task lifecycle state machine is isolated from payroll logic.

## Dependencies

- `story-01-identity.md` for `User` and `Department`.
- `story-04-collaboration-audit.md` for audit and notification wiring.

## Related Stories

- `story-03-payroll.md` consumes `TaskSubmission` and `TaskType`.
