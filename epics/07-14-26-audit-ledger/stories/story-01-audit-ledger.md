---
date_created: 2026-07-14
date_modified: 2026-07-15
title: "US-01: View Audit Logs and Ledger"
description: Admins and HR can query immutable audit logs and financial ledger entries.
sprint: 1
points: 5
---

# US-01: View Audit Logs and Ledger

## Status

CLOSED. Audit/ledger views are implemented in the frontend `/audit` page with filtered audit logs and ledger summaries, backed by `/api/audit-ledger/*` reporting endpoints. Verified by `tests/epics/test_epic_workflow.py` (audit/ledger immutability test passes).

## Story

As an **admin or HR user**, I want to **search audit logs and ledger entries** so that **I can trace every action and financial change in the system**.

## Acceptance Criteria

- **GIVEN** an admin queries audit logs, **WHEN** they provide filters for `reference_entity`, `reference_id`, `action`, `actor_id`, or a date range, **THEN** the API returns paginated, chronologically ordered results with parsed `old_values` and `new_values` JSON.
- **GIVEN** an HR user views the ledger, **WHEN** they filter by `user_id`, `entry_type`, `period`, or `reference_entity`, **THEN** the API returns paginated entries with a running total and per-entry-type breakdown.
- **GIVEN** any user with write access, **WHEN** they attempt to update or delete an `AuditLog` or `Ledger` record through the generic entity API, **THEN** the system returns an explicit error stating these records are immutable and does not modify the data.
- **GIVEN** a ledger report request, **WHEN** HR groups by `entry_type`, `user`, `period`, or `reference_entity`, **THEN** the response includes grouped totals and the full detail list for reconciliation.
- **GIVEN** an audit report request, **WHEN** an admin groups by `action`, `actor`, or `reference_entity`, **THEN** the response includes grouped counts and the full detail list for compliance review.

## Models

- `AuditLog`
- `Ledger`

## Implementation Notes

- Reuse `collaboration_audit` module models.
- Use the generic entity query service for filtering.
- DRY: reuse the same reporting patterns for both audit and ledger.
- SOLID: reporting logic is separate from storage.

## Dependencies

- `epics/07-14-26-foundation-modules/stories/story-04-collaboration-audit.md`

## Related Stories

- `epics/07-14-26-payroll-automation/stories/story-01-payroll-automation.md`
