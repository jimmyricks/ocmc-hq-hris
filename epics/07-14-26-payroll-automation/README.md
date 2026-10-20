---
date_created: 2026-07-14
date_modified: 2026-07-15
title: Payroll Automation
description: Bi-monthly payroll calculation and disbursement based on approved task submissions.
---

# Epic: Payroll Automation

## Goal

Automatically calculate user payroll twice per month using approved task submissions and produce immutable ledger and audit records.

## Scope

- `PayrollPeriod` creation for bi-monthly cycles.
- Payroll engine scanning approved `TaskSubmission` records.
- `PayrollEntry` and `PayrollLineItem` generation.
- Disbursement and `Ledger` debit entries.
- Out of scope: external bank integrations, tax calculations.

## Modules and Models

- `payroll` module:
  - `PayrollPeriod`
  - `PayrollEntry`
  - `PayrollLineItem`
- `project_tasks` module:
  - `TaskSubmission`
  - `TaskType`
- `collaboration_audit` module:
  - `Ledger`
  - `AuditLog`

## Sprint Plan

- **Sprint 1:** Payroll period generation and line-item creation.
- **Sprint 2:** Approval, disbursement, and ledger debit entries.

## Status

CLOSED. Backend `PayrollPeriod`/`PayrollEntry`/`PayrollLineItem` services and endpoints are implemented and tested (`/api/payroll/periods`, `/api/payroll/periods/generate`, `/api/payroll/entries/{id}/approve`, `/api/payroll/entries/{id}/pay`). Frontend `/payroll` page is created, wired in the sidebar, and supports period creation, payroll generation, entry approval, and disbursement. Verified by `tests/epics/test_epic_workflow.py` (payroll generation and payment tests pass).

## Definition of Done

- Payroll can be generated for a period covering 1st-15th or 16th-end of month.
- Only approved `TaskSubmission` rows within the period are included.
- `PayrollLineItem.amount = TaskType.unit_rate * quantity`.
- `PayrollEntry.total_amount` is the sum of line items.
- Disbursement writes a `Ledger` debit for the user.
- `AuditLog` captures every payroll generation and payment event.
- All acceptance criteria in the linked stories pass.

## References

- `docs/erd/ERD.md`
- `docs/architecture/ARCHITECTURE.md`
- `docs/hris/HRIS.md`
- `epics/07-14-26-foundation-modules/README.md`
