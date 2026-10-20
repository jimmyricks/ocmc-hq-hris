---
date_created: 2026-07-14
date_modified: 2026-07-15
title: Work Submission
description: Users submit assigned tasks with an external deliverable link and track submission history.
---

# Epic: Work Submission

## Goal

Allow users to submit their completed work for a task, provide an externally stored deliverable link (e.g. Google Drive), and handle revisions when the project manager requests changes.

## Scope

- Task submission creation with version tracking.
- External link capture on `TaskSubmission` (`external_link`) for traceability to outside media.
- Submission revision chain (`previous_submission_id`).
- Out of scope: file upload storage, approval decisions, payroll calculation.

## Modules and Models

- `project_tasks` module:
  - `TaskSubmission`

## Sprint Plan

- **Sprint 1:** Task submission and version history.
- **Sprint 2:** External link capture and submission revision workflow.

## Status

CLOSED. The `/tasks/my` page provides a submit-for-review dialog that captures `external_link`, creates `TaskSubmission` records, and uses `previous_submission_id` to build the revision chain. Backend `TaskSubmissionService` enforces assignee-only submissions and version incrementing. Verified by `tests/epics/test_epic_workflow.py` (submission, non-assignee rejection, and revision chain tests pass).

## Definition of Done

- Users can create a `TaskSubmission` against a `TaskAssignment`.
- Each submission can reference the previous submission for revision tracking.
- Submissions capture an `external_link` (e.g. Google Drive URL) instead of uploading files.
- Revision and submission events write `AuditLog` entries.
- All acceptance criteria in the linked stories pass.

## References

- `docs/erd/ERD.md`
- `docs/architecture/ARCHITECTURE.md`
- `docs/hris/HRIS.md`
- `epics/07-14-26-foundation-modules/README.md`
