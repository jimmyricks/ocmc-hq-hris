---
date_created: 2026-07-14
date_modified: 2026-07-15
title: "US-01: Generate and Pay Payroll"
description: HR generates bi-monthly payroll from approved submissions and processes disbursement.
sprint: 1
points: 8
---

# US-01: Generate and Pay Payroll

## Status

CLOSED. Backend bi-monthly payroll generation, approval, and disbursement are implemented and tested. Frontend `/payroll` page is wired to create periods, generate entries, approve, and pay. Verified by `tests/epics/test_epic_workflow.py` (payroll generation and payment tests pass).

## Story

As an **HR user**, I want to **generate payroll for a bi-monthly period and process disbursement** so that **users are paid for approved work on time**.

## Acceptance Criteria

- **GIVEN** an HR user creates a bi-monthly `PayrollPeriod` covering the 1st-15th or 16th-end of a month, **WHEN** the period is saved, **THEN** `start_date` must be before `end_date`, `cutoff` cannot exceed `end_date`, and the period status is `open`.
- **GIVEN** an open `PayrollPeriod`, **WHEN** payroll is generated, **THEN** the engine includes only `approved` `TaskSubmission` rows whose `submitted_at` falls inside the period, excludes already-paid or draft submissions, and groups results by user.
- **GIVEN** an approved submission included in payroll, **WHEN** a `PayrollLineItem` is created, **THEN** `rate` is copied from the related `TaskType.unit_rate`, `quantity` defaults to `1`, and `amount = rate * quantity` rounded to two decimals.
- **GIVEN** a `PayrollEntry` with one or more line items, **WHEN** the entry is saved, **THEN** `total_tasks` equals the number of line items and `total_amount` equals the sum of all `amount` values.
- **GIVEN** a generated `PayrollEntry` in `draft` status, **WHEN** HR approves it, **THEN** the status moves to `approved`, `approved_by` and `approved_at` are recorded, and an `AuditLog` entry is created.
- **GIVEN** an `approved` `PayrollEntry`, **WHEN** HR marks it paid, **THEN** a `Ledger` debit equal to `total_amount` is recorded for the user, the `PayrollEntry` status becomes `paid`, the parent `PayrollPeriod` status becomes `paid`, the user is notified, and an `AuditLog` entry is created.
- **GIVEN** a `PayrollPeriod` already marked `paid`, **WHEN** a user attempts to regenerate payroll, **THEN** the system rejects the request to prevent accidental reprocessing.

## Models

- `PayrollPeriod`
- `PayrollEntry`
- `PayrollLineItem`
- `TaskSubmission`
- `TaskType`
- `Ledger`
- `Notification`
- `AuditLog`

## Implementation Notes

- Reuse `payroll`, `project_tasks`, and `collaboration_audit` module models.
- Payroll generation is wrapped in a database transaction.
- Ledger entries are written by a payroll domain service.
- DRY: reuse the generic `Ledger` and `Notification` services.

## Dependencies

- `epics/07-14-26-hr-verification-approval/stories/story-01-hr-verification-approval.md`
- `epics/07-14-26-foundation-modules/stories/story-03-payroll.md`

## Related Stories

- `epics/07-14-26-audit-ledger/stories/story-01-audit-ledger.md`
