---
date_created: 2026-07-14
date_modified: 2026-07-15
title: "US-04: Collaboration & Audit Module"
description: Scaffold Comment, Ledger, AuditLog, and Notification
sprint: 3
points: 8
---

# US-04: Collaboration & Audit Module

## Status

CLOSED. `Comment`, `Ledger`, `AuditLog`, and `Notification` models and JSON metadata are scaffolded in `backend/app/modules/collaboration_audit/`. `Ledger` credits/debits are written by the approval and payroll domain services, and `AuditLog`/`Ledger` immutability is enforced by the generic entity API. The frontend `/audit` page exposes Audit Logs and Ledger views. Verified by `tests/epics/test_epic_workflow.py` (audit/ledger update/delete rejected test passes).

## Story

As a **system**, I want to **log comments, audit events, ledger entries, and notifications** so that **every action and financial change is traceable and users are notified**.

## Acceptance Criteria

- **GIVEN** any header entity, **WHEN** a user adds a comment, **THEN** a `Comment` row is created with `reference_entity` and `reference_id`.
- **GIVEN** a `TaskSubmission` or `PayrollEntry`, **WHEN** a user provides an external link, **THEN** the link is stored on the record; no `File` entity is used.
- **GIVEN** a state change, **WHEN** the transaction commits, **THEN** an `AuditLog` row is written with `old_values` and `new_values`.
- **GIVEN** a financial event, **WHEN** it is approved, **THEN** a `Ledger` row is written with `entry_type` and `amount`.
- **GIVEN** a state change that affects a user, **WHEN** it happens, **THEN** a `Notification` is created.

## Models

- `Comment`
- `Ledger`
- `AuditLog`
- `Notification`

## Implementation Notes

- Use `forge.py` to scaffold each entity.
- Polymorphic `reference_entity` + `reference_id` pattern.
- File attachments are intentionally not part of this system; deliverable links are stored on `TaskSubmission` instead.
- `Ledger` is written by hooks or domain services, not by route handlers.
- DRY: one generic service for polymorphic comments and notifications.
- SOLID: small interfaces for audit and ledger so other modules depend on abstractions.

## Dependencies

- `story-01-identity.md` for `User` (actor, comment_by).
- Can be developed in parallel with `story-03-payroll.md` once the base entities exist.
