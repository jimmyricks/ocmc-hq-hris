---
date_created: 2026-07-23
date_modified: 2026-07-23
title: "US-03: Link Shortener with Click Logs"
description: Full vertical slice for creating, listing, editing, redirecting short links and recording click logs.
sprint: 2
points: 8
---

# US-03: Link Shortener with Click Logs

## Story

As an **authenticated user**, I want to **shorten long URLs, manage my short links, and see click analytics** so that **I can share clean links and track engagement like Bitly**.

## Acceptance Criteria

- **GIVEN** I am authenticated, **WHEN** I submit a destination URL (and optional custom slug, title, expiration) on `/utils/links`, **THEN** the API creates a `ShortLink` with a unique slug, validates the URL scheme is `http`/`https`, rejects `javascript:`/`data:` URIs, and returns the short URL.
- **GIVEN** a short link exists, **WHEN** I request `/{slug}` (the public redirect endpoint), **THEN** the API responds with a redirect to the destination URL and writes an immutable `ShortLinkClick` record (timestamp, hashed IP, user agent, referer) and increments `click_count`.
- **GIVEN** I am the owner (or an admin), **WHEN** I open the link detail view, **THEN** I see aggregate analytics (total clicks, recent clicks, referer/country breakdown) sourced from `ShortLinkClick`.
- **GIVEN** I am the owner, **WHEN** I edit the destination, title, or expiration, or deactivate a link, **THEN** the `ShortLink` is updated and an `AuditLog` entry is written.
- **GIVEN** a link is deactivated or past `expires_at`, **WHEN** a redirect is requested, **THEN** the API returns a 410 Gone (or a configurable expired page) and does not redirect.
- **GIVEN** I list my short links, **WHEN** I filter by active/expired or search by slug/title, **THEN** the API returns paginated results scoped to my links (admins see all).

## Models

- `ShortLink`
- `ShortLinkClick`
- `AuditLog` (side effect)

## Implementation Notes

- Slug generation: default to a short random code (e.g. 6-7 char base62); allow optional custom slugs with uniqueness validation and a safe charset allowlist.
- Store IP addresses hashed/truncated for privacy; do not log raw PII in `ShortLinkClick`. Redact sensitive query parameters per the security model in [`docs/features/UTILS.md`](../../../docs/features/UTILS.md).
- The redirect endpoint is public (no auth) but creation/management is authenticated.
- Reuse the generic entity query service for list/detail; use dedicated endpoints for create/redirect to keep validation and side effects explicit.
- DRY: reuse existing `AuditLog` wiring from `collaboration_audit`.
- This story is independent of `story-04-qr-generator.md`; the two share no files.

## Dependencies

- `story-01-utils-module-scaffold.md` (entities and migrations).
- `story-02-frontend-shell-sidebar.md` (the `/utils/links` route placeholder).

## Related Stories

- `story-05-link-security-abuse-prevention.md` hardens the create and redirect paths built here.
- `story-04-qr-generator.md` can optionally reference a `ShortLink` via `QrCode.short_link_id`.
