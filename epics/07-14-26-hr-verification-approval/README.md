---
date_created: 2026-07-14
date_modified: 2026-07-15
title: HR Verification & Approval
description: Project managers and HR review, approve, or reject task submissions and trigger payroll eligibility.
---

# Epic: HR Verification & Approval

## Goal

Provide a review workflow where project managers and HR can approve or reject task submissions, request revisions, and mark work as eligible for payroll.

## Scope

- `TaskApproval` decisions for submissions.
- Status transitions on `TaskSubmission` and `Task`.
- Notifications to users on decisions.
- `Ledger` credit entries for approved work.
- Out of scope: payroll generation, disbursement.

## Modules and Models

- `project_tasks` module:
  - `Task`
  - `TaskSubmission`
  - `TaskApproval`
- `collaboration_audit` module:
  - `Notification`
  - `Ledger`
  - `AuditLog`

## Sprint Plan

- **Sprint 1:** Task approval and status transitions.
- **Sprint 2:** Ledger credit entries and notification dispatch.

## Status

CLOSED. The `/submissions` review page lets project managers and HR approve, reject, or request revisions on `TaskSubmission` records. Backend `TaskApprovalService` updates submission/task statuses, writes `Ledger` credits for approvals, and creates notifications. Verified by `tests/epics/test_epic_workflow.py` (approval approved/rejected tests pass).

## Definition of Done

- PMs can approve, reject, or request revisions on a `TaskSubmission`.
- `Task` and `TaskSubmission` statuses update consistently.
- `Notification` is created for the user on every decision.
- Approved submissions write a `Ledger` credit with `entry_type='credit'`.
- `AuditLog` captures every approval decision.
- All acceptance criteria in the linked stories pass.

## References

- `docs/erd/ERD.md`
- `docs/architecture/ARCHITECTURE.md`
- `docs/hris/HRIS.md`
- `epics/07-14-26-foundation-modules/README.md`
