---
date_created: 2026-07-14
date_modified: 2026-07-15
title: "US-01: Review and Approve Submissions"
description: Project managers and HR review task submissions, approve or reject them, and notify users.
sprint: 1
points: 8
---

# US-01: Review and Approve Submissions

## Status

CLOSED. The `/submissions` review page lets project managers and HR approve, reject, or request revisions on `TaskSubmission` records. Backend `TaskApprovalService` updates submission/task statuses, writes `Ledger` credits for approvals, and creates notifications. Verified by `tests/epics/test_epic_workflow.py` (approval approved and approval rejected tests pass).

## Story

As a **project manager or HR user**, I want to **review task submissions, approve or reject them, and request revisions** so that **only verified work becomes eligible for payroll**.

## Acceptance Criteria

- **GIVEN** a `TaskSubmission` in `submitted` or `under_review` status, **WHEN** a project manager or HR user records a `TaskApproval`, **THEN** the decision must be `approved`, `rejected`, or `needs_revision`; `rejected` and `needs_revision` decisions require non-empty remarks.
- **GIVEN** an approval decision, **WHEN** it is `approved`, **THEN** the `TaskSubmission` status becomes `approved`, the parent `Task` status becomes `approved`, the user receives a `Ledger` credit equal to the task type's `unit_rate` (default quantity `1`), and the user is notified that the work is approved.
- **GIVEN** a `needs_revision` decision, **WHEN** it is saved, **THEN** the `TaskSubmission` status becomes `needs_revision`, the `Task` status becomes `needs_revision`, the user receives a notification with the exact remarks explaining what to fix, and no ledger entry is created.
- **GIVEN** a `rejected` decision, **WHEN** it is saved, **THEN** the `TaskSubmission` status becomes `rejected`, the `Task` returns to `in_progress` so it can be reassigned or reworked, the user is notified with the rejection reason, and no ledger entry is created.
- **GIVEN** a submission that is already `approved` or `rejected`, **WHEN** a user attempts to record another approval, **THEN** the system rejects the request to prevent duplicate decisions.
- **GIVEN** any approval decision, **THEN** an immutable `AuditLog` row is written with `reference_entity='task_submission'`, the actor, the `old_values` and `new_values` of the submission status, and a timestamp.

## Models

- `TaskSubmission`
- `TaskApproval`
- `Task`
- `Ledger`
- `Notification`
- `AuditLog`

## Implementation Notes

- Reuse `project_tasks` and `collaboration_audit` module models.
- Ledger credit is written by a domain service, not by route handlers.
- DRY: use the generic `Notification` service for user alerts.
- SOLID: approval logic is separate from submission and payroll logic.

## Dependencies

- `epics/07-14-26-work-submission/stories/story-01-work-submission.md`
- `epics/07-14-26-foundation-modules/stories/story-04-collaboration-audit.md`

## Related Stories

- `epics/07-14-26-payroll-automation/stories/story-01-payroll-automation.md`
