---
date_created: 2026-07-14
date_modified: 2026-07-14
title: "US-03: Payroll Module"
description: Scaffold PayrollPeriod, PayrollEntry, and PayrollLineItem
sprint: 3
points: 8
---

# US-03: Payroll Module

## Status

CLOSED. `PayrollPeriod`, `PayrollEntry`, and `PayrollLineItem` models and JSON metadata are scaffolded in `backend/app/modules/payroll/`. The frontend `/payroll` page is wired in the sidebar and supports period creation, payroll generation, entry approval, and disbursement. Verified by `tests/epics/test_epic_workflow.py` (payroll generation and payment tests pass).

## Story

As an **HR user**, I want to **generate payroll periods and entries from approved task submissions** so that **users are paid on time**.

## Acceptance Criteria

- **GIVEN** a pay date, **WHEN** the payroll engine runs, **THEN** it creates a `PayrollPeriod` for the correct half-month.
- **GIVEN** an approved `TaskSubmission` within a period, **WHEN** the payroll engine runs, **THEN** it creates a `PayrollLineItem` using `TaskType.unit_rate`.
- **GIVEN** a `PayrollEntry`, **WHEN** HR approves it, **THEN** a `Ledger` credit entry is recorded and the entry becomes `approved`.
- **GIVEN** a `PayrollEntry`, **WHEN** it is paid, **THEN** a `Ledger` debit entry is recorded.

## Models

- `PayrollPeriod`
- `PayrollEntry`
- `PayrollLineItem` (detail of `PayrollEntry`)

## Implementation Notes

- Use `forge.py` to scaffold each entity.
- The payroll engine is a scheduler/service, but `PayrollEntry` domain logic lives in `modules/payroll/entities/PayrollEntry.py`.
- DRY: reuse `Ledger` and `AuditLog` from the collaboration module.
- SOLID: payroll calculation depends on a `TaskSubmission` interface, not project internals.

## Dependencies

- `story-02-project-tasks.md` for `TaskSubmission` and `TaskType`.
- `story-04-collaboration-audit.md` for `Ledger` and `AuditLog`.
