---
date_created: 2026-07-23
date_modified: 2026-07-23
title: "US-01: Scaffold Utils Module and Entities"
description: Scaffold the utils module with ShortLink, ShortLinkClick, and QrCode entities and migrations.
sprint: 1
points: 5
---

# US-01: Scaffold Utils Module and Entities

## Story

As a **developer**, I want to **scaffold the `utils` module with its entities and migrations** so that **the link shortener and QR generator features have a persistence layer to build on**.

## Acceptance Criteria

- **GIVEN** the `utils` module does not exist, **WHEN** I run `forge.py` to scaffold the module, **THEN** `backend/app/modules/utils/` is created with `entities/` and `models/` subdirectories following the same layout as `collaboration_audit`.
- **GIVEN** the entity metadata files are defined, **WHEN** I run `forge sync`, **THEN** SQLAlchemy models for `ShortLink`, `ShortLinkClick`, and `QrCode` are generated and `forge sync` completes with zero errors.
- **GIVEN** the models are generated, **WHEN** I apply migrations, **THEN** the `oc_short_link`, `oc_short_link_click`, and `oc_qr_code` tables are created with the columns defined in [`docs/features/UTILS.md`](../../../docs/features/UTILS.md).
- **GIVEN** the entities are registered, **WHEN** the meta registry loads, **THEN** `ShortLink`, `ShortLinkClick`, and `QrCode` are discoverable via the generic entity API for list/detail queries.

## Models

- `ShortLink` (header)
- `ShortLinkClick` (detail/log of `ShortLink`)
- `QrCode` (header)

## Implementation Notes

- Use `forge.py` to generate metadata and models; do not hand-write boilerplate.
- `ShortLinkClick` is a detail entity of `ShortLink` (`parent_entity: ShortLink`, `child_parent_fk_field: short_link_id`) and is append-only/immutable.
- Follow the header/detail and generic/polymorphic patterns from `docs/erd/ERD.md`.
- Register entities in the meta registry so the generic entity API can query them; restrict write paths to dedicated endpoints built in Sprint 2.

## Dependencies

- None. This is the foundation story for the epic.

## Related Stories

- `story-03-link-shortener-with-logs.md` depends on this story for `ShortLink`/`ShortLinkClick`.
- `story-04-qr-generator.md` depends on this story for `QrCode`.
