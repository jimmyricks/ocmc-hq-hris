---
date_created: 2026-07-14
date_modified: 2026-07-15
title: Foundation - Core Modules and Data Models
description: First epic to scaffold all modules and models for OC HQ
---

# Epic: Foundation - Core Modules and Data Models

## Goal

Deliver the shared data model that all other features depend on.

## Scope

- All modules and entities from `docs/erd/ERD.md` v3.
- Header/detail, generic/polymorphic, and audit/ledger patterns.
- Out of scope: UI pages, business automation, reports.

## Modules and Models

1. **Identity & HR** — `User` and `Department`
2. **Project & Tasks** — `Project`, `TaskType`, `Task`, `TaskAssignment`, `TaskSubmission`, `TaskApproval`
3. **Payroll** — `PayrollPeriod`, `PayrollEntry`, `PayrollLineItem`
4. **Collaboration & Audit** — `Comment`, `Ledger`, `AuditLog`, `Notification`

## Sprint Plan

- **Sprint 1: Identity & HR**
  - `story-01-identity.md`
- **Sprint 2: Project & Tasks**
  - `story-02-project-tasks.md`
- **Sprint 3: Payroll & Collaboration/Audit**
  - `story-03-payroll.md`
  - `story-04-collaboration-audit.md`

## Status

CLOSED. Backend modules (`identity_hr`, `project_tasks`, `payroll`, `collaboration_audit`) and entity JSON metadata are scaffolded, the generic entity API contract is tested, and the frontend uses the real `Project`, `Task`, `TaskType`, `TaskCategory`, `PayrollPeriod`, `PayrollEntry`, `PayrollLineItem`, `AuditLog`, and `Ledger` entities. Verified by `tests/api/test_generic_entity_api_20260723.py` (7/7) and `tests/epics/test_epic_workflow.py` (9/9).

## Definition of Done

- Each entity has a JSON metadata file and generated model.
- All relationships match `docs/erd/ERD.md` v3.
- `forge sync` completes with zero errors.
- `AuditLog` and `Ledger` wiring for state/financial changes is deferred to the `07-14-26-audit-ledger` and `07-14-26-payroll-automation` epics.
- All stories are reviewed and linked to ERD/Architecture docs.

## Generated Artifacts

- `backend/app/modules/identity_hr/`
- `backend/app/modules/project_tasks/`
- `backend/app/modules/payroll/`
- `backend/app/modules/collaboration_audit/`

## References

- `docs/INDEX.md`
- `docs/erd/ERD.md`
- `docs/architecture/ARCHITECTURE.md`
- `docs/hris/HRIS.md`
- `epics/DEVIN.md`
