---
date_created: 2026-07-14
date_modified: 2026-07-15
title: "US-01: Manage Projects and Tasks"
description: Project managers can create projects, define task types, and assign tasks with status tracking.
sprint: 1
points: 8
---

# US-01: Manage Projects and Tasks

## Status

CLOSED. The project task board (`project/[id]`, task table/modal, `nav-projects`) uses the backend `Task`, `TaskType`, `TaskCategory`, and `Project` entities with no mapping. Status values follow the real lifecycle (`pending` → `in_progress` → `submitted` → `approved`/`closed`). Verified by `tests/api/test_project_task_api_20260723.py` (8/8) and `tests/epics/test_epic_workflow.py` (assignment lifecycle test passes).

## Story

As a **project manager**, I want to **create projects, define task types, and assign tasks to users** so that **work is organized, tracked, and ready for review**.

## Acceptance Criteria

- **GIVEN** a project manager creates a project, **WHEN** the project is saved, **THEN** it is assigned a unique code, a default status of `active`, and start/end dates that cannot be inverted.
- **GIVEN** an active project, **WHEN** a project manager defines a task type, **THEN** the type stores a unit rate, unit of measure (`per_task`, `per_hour`, `per_file`, or `per_unit`), and whether submissions require approval before payment.
- **GIVEN** an active project and a valid task type, **WHEN** a task is created, **THEN** the system auto-generates a unique `task_key` from the project code (e.g. `OCHQ-101`), sets status to `pending`, and records `created_by`, `last_modified_by`, and timestamps.
- **GIVEN** a task in `pending` or `in_progress` status, **WHEN** it is assigned to a user, **THEN** any previous active assignment is marked `reassigned` with an `unassigned_at` timestamp, the new assignment becomes the only active one, the task moves to `in_progress`, and the user receives a notification.
- **GIVEN** an assignment attempt on a task that is `approved`, `closed`, or `cancelled`, **WHEN** the request is made, **THEN** the system rejects it with a clear error and does not create an assignment record.
- **GIVEN** any project, task, or assignment is created or updated, **THEN** an `AuditLog` row records the entity, record id, action, actor, old/new values, and timestamp.

## Models

- `Project`
- `TaskType`
- `Task`
- `TaskAssignment`

## Implementation Notes

- Reuse `project_tasks` module and models from `epics/07-14-26-foundation-modules`.
- Use `forge.py` to add any new fields needed.
- Business logic lives in `modules/project_tasks/entities/`.
- DRY: use generic `Notification` and `AuditLog` services.

## Dependencies

- `epics/07-14-26-foundation-modules/stories/story-02-project-tasks.md`
- `epics/07-14-26-foundation-modules/stories/story-01-identity.md`

## Related Stories

- `epics/07-14-26-work-submission/stories/story-01-work-submission.md`
