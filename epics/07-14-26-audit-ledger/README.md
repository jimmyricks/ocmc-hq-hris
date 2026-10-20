---
date_created: 2026-07-14
date_modified: 2026-07-15
title: Audit & Ledger
description: Immutable audit logs, financial ledgers, and reporting for compliance and traceability.
---

# Epic: Audit & Ledger

## Goal

Provide a transparent, immutable record of every system action and financial event, with views and reports for administrators and auditors.

## Scope

- Query and filter `AuditLog` and `Ledger` records.
- Reporting for audit trails and financial summaries.
- Read-only views for audit and ledger data.
- Out of scope: modifying or deleting audit/ledger records.

## Modules and Models

- `collaboration_audit` module:
  - `AuditLog`
  - `Ledger`
  - `Notification`

## Sprint Plan

- **Sprint 1:** Audit log and ledger query views.
- **Sprint 2:** Audit and financial reports.

## Status

CLOSED. Backend `/api/audit-ledger/audit-logs` and `/api/audit-ledger/ledger` endpoints provide filtered, paginated reporting. Frontend `/audit` page delivers tabbed Audit Logs and Ledger views with filters and a ledger summary; the Audit menu is wired in the sidebar. Verified by `tests/epics/test_epic_workflow.py` (audit/ledger immutability test passes).

## Definition of Done

- Admins can search audit logs by entity, record id, actor, and date range.
- HR can view ledger summaries by user and period.
- Audit and ledger records are immutable and cannot be updated or deleted.
- Reports respect the generic `reference_entity`/`reference_id` pattern.
- All acceptance criteria in the linked stories pass.

## References

- `docs/erd/ERD.md`
- `docs/architecture/ARCHITECTURE.md`
- `docs/hris/HRIS.md`
- `epics/07-14-26-foundation-modules/README.md`
