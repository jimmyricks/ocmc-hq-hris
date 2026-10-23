---
date_created: 2026-07-14
date_modified: 2026-07-15
title: "US-01: Submit Work and Provide External Link"
description: Users can submit work for a task, provide an external deliverable link, and revise submissions.
sprint: 1
points: 8
---

# US-01: Submit Work and Provide External Link

## Status

CLOSED. The `/tasks/my` page provides a submit-for-review dialog that captures `external_link`, creates `TaskSubmission` records, and uses `previous_submission_id` to build the revision chain. Backend `TaskSubmissionService` enforces assignee-only submissions and version incrementing. Verified by `tests/epics/test_epic_workflow.py` (submission, non-assignee rejection, and revision chain tests pass).

Update: each `TaskType` now declares a `submission_mode` (`link` or `text`). Link-mode submissions require `external_link`; text-mode submissions require `content` (pasted deliverable text). The task keeps one current deliverable: submitting a link upserts the task's `task_link`, and active project members see the current deliverable (link or text) through member-safe task summaries — they cannot read raw submission records. Verified by `tests/application/test_task_deliverables.py`.

## Story

As a **user**, I want to **submit completed work for a task and provide an external link** (e.g. Google Drive) so that **project managers can review and approve it**.

## Acceptance Criteria

- **GIVEN** a task assigned to an active user, **WHEN** the user creates a submission, **THEN** the `TaskSubmission` links to the active `TaskAssignment`, version starts at `1`, status becomes `submitted`, the task status moves to `submitted`, and the project manager is notified.
- **GIVEN** a user who is not the assignee, **WHEN** they attempt to create a submission, **THEN** the system rejects the request and no submission is created.
- **GIVEN** a task that is `approved`, `closed`, or `cancelled`, **WHEN** a user attempts to submit work, **THEN** the system rejects the request with a clear business error.
- **GIVEN** a submission, **WHEN** the user provides an `external_link`, **THEN** the `TaskSubmission` stores the URL (e.g. Google Drive) for easy traceability without uploading files to the system.
- **GIVEN** a task type configured with `submission_mode = "link"`, **WHEN** a submission is created, **THEN** an external link is required and the task's single current `task_link` is created or updated to match it.
- **GIVEN** a task type configured with `submission_mode = "text"`, **WHEN** a submission is created, **THEN** `content` is required and stored on the submission instead of a link.
- **GIVEN** an active project member who is not the assignee, **WHEN** they view the project task table or task details, **THEN** they see the active assignee and the current deliverable, but not raw submission, approval, or payroll fields.
- **GIVEN** a submission marked `needs_revision`, **WHEN** the user resubmits, **THEN** a new `TaskSubmission` is created with `previous_submission_id` pointing to the prior version, the version is incremented monotonically for that assignment, and the task status returns to `submitted`.
- **GIVEN** any submission create event, **THEN** an immutable `AuditLog` row is written with the actor, timestamp, and affected record; the submitter receives a confirmation or revision notification.

## Models

- `TaskSubmission`

## Implementation Notes

- Reuse `project_tasks` module models.
- Store `external_link` on `TaskSubmission` for link deliverables and `content` for pasted-text deliverables; which one is required depends on the task type's `submission_mode`.
- Each versioned `TaskSubmission` keeps its own deliverable snapshot for audit/payroll, while the task's `task_link` row always reflects the current link.
- File uploads are intentionally not part of this workflow; keep system uploads limited to profile pictures and system configuration.

## Dependencies

- `epics/07-14-26-project-task-management/stories/story-01-project-and-task-management.md`
- `epics/07-14-26-foundation-modules/stories/story-04-collaboration-audit.md`

## Related Stories

- `epics/07-14-26-hr-verification-approval/stories/story-01-hr-verification-approval.md`
