---
date_created: 2026-07-14
date_modified: 2026-07-15
title: Project & Task Management
description: Create projects, assign tasks, and track statuses end-to-end.
---

# Epic: Project & Task Management

## Goal

Enable project managers to create projects, define task types, assign tasks to users, and track task status through the project lifecycle.

## Scope

- Project CRUD and project manager assignment.
- Task type definitions with unit rates and approval rules.
- Task creation, assignment, and status transitions.
- Out of scope: payroll generation, file uploads, submission approval.

## Modules and Models

- `project_tasks` module:
  - `Project`
  - `TaskType`
  - `Task`
  - `TaskAssignment`

## Sprint Plan

- **Sprint 1:** Project and task type management.
- **Sprint 2:** Task lifecycle and assignment.

## Status

CLOSED. The project task board (`project/[id]`, task table/modal, `nav-projects`) uses the backend `Task`, `TaskType`, `TaskCategory`, and `Project` entities with no mapping. Status values follow the real lifecycle (`pending` → `in_progress` → `submitted` → `approved`/`closed`). Verified by `tests/api/test_project_task_api_20260723.py` (8/8) and `tests/epics/test_epic_workflow.py`.

## Definition of Done

- PMs can create projects and task types.
- Tasks can be assigned to users with due dates and priority.
- Task status transitions follow `pending -> in_progress -> submitted -> approved/closed`.
- Every create/update writes an `AuditLog` entry.
- All acceptance criteria in the linked stories pass.

## References

- `docs/erd/ERD.md`
- `docs/architecture/ARCHITECTURE.md`
- `epics/07-14-26-foundation-modules/README.md`
