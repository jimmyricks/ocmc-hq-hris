---
date_created: 2026-07-14
date_modified: 2026-07-14
title: "US-01: Identity & HR Module"
description: Scaffold User and Department entities
sprint: 1
points: 8
---

# US-01: Identity & HR Module

## Status

CLOSED. `User` and `Department` entities are scaffolded in `backend/app/modules/identity_hr/` (models and JSON metadata), the generic entity API exposes them, and the `/admin` users page provides full user CRUD against `/api/admin/users`. Login and `auth.ts` are wired. Verified by `tests/api/test_generic_entity_api_20260723.py` (7/7 pass).

## Story

As an **admin**, I want to **manage users and departments** so that **the platform can authenticate users and organize them by role and department**.

## Acceptance Criteria

- **GIVEN** an admin, **WHEN** they create a user, **THEN** the user has email, password_hash, role, status, and full name.
- **GIVEN** a user, **WHEN** they are assigned to a department, **THEN** the `department` field references the department.
- **GIVEN** a department, **WHEN** a head is assigned, **THEN** it references a user.
- **GIVEN** any create/update, **THEN** an `AuditLog` row is written with `old_values` and `new_values`.

## Models

- `User`
- `Department`

## Implementation Notes

- Use `python -m app.forge new-entity` to generate JSON metadata and models.
- Business logic: `modules/identity_hr/entities/{User,Department}.py`.
- Follow Clean + Hybrid Architecture: validation and state rules live in the entity `.py` files.
- DRY: reuse base timestamps and audit fields from `core/base_model.py`.
- SOLID: one entity per file; depend on repository abstractions, not the database directly.

## Dependencies

- `core/base_model.py` and `core/security.py` for password hashing and audit fields.

## Related Stories

- `story-02-project-tasks.md` uses `User` and `Department`.
