---
date_created: 2026-07-23
date_modified: 2026-07-23
title: "US-02: Utils Sidebar Entry and Page Shell"
description: Add a Utils group to the sidebar and build the /utils page shell with tabbed routing for the tools.
sprint: 1
points: 3
---

# US-02: Utils Sidebar Entry and Page Shell

## Story

As a **user**, I want to **open a Utils page from the sidebar** so that **I can access the link shortener and QR generator tools in one place**.

## Acceptance Criteria

- **GIVEN** the sidebar configuration in `src/lib/components/app-sidebar.svelte`, **WHEN** the app loads, **THEN** a "Utils" group is visible with sub-items "Link Shortener" (`/utils/links`) and "QR Generator" (`/utils/qr`).
- **GIVEN** I navigate to `/utils`, **WHEN** the page loads, **THEN** a tabbed shell renders with "Link Shortener" and "QR Generator" tabs and defaults to the Link Shortener tab.
- **GIVEN** I select a tab, **WHEN** the route changes to `/utils/links` or `/utils/qr`, **THEN** the corresponding placeholder component renders without errors.
- **GIVEN** the Utils group, **WHEN** rendered, **THEN** it uses an appropriate lucide icon (e.g. `Wrench` or `Link2`) and follows the existing `navSecondary` collapsible pattern.

## Models

- None (frontend only).

## Implementation Notes

- Add the Utils entry to `navSecondary` in `src/lib/components/app-sidebar.svelte`, mirroring the existing "System Admin" group structure.
- Create `frontend/src/routes/utils/+page.svelte` (tabbed shell) and `frontend/src/routes/utils/links/+page.svelte` and `frontend/src/routes/utils/qr/+page.svelte` placeholders.
- Reuse the existing sidebar/collapsible components; do not introduce new UI primitives.
- This story is frontend-only and shares no files with `story-01-utils-module-scaffold.md`, so the two can be worked in parallel.

## Dependencies

- None.

## Related Stories

- `story-03-link-shortener-with-logs.md` fills in the `/utils/links` page.
- `story-04-qr-generator.md` fills in the `/utils/qr` page.
