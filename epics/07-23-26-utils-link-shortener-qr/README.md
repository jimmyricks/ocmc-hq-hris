---
date_created: 2026-07-23
date_modified: 2026-07-23
title: Utils - Link Shortener and QR Generator
description: Self-hosted Bitly-style link shortener with click logs and a QR code generator, exposed under a Utils page in the sidebar.
---

# Epic: Utils - Link Shortener and QR Generator

## Goal

Deliver a secure, self-hosted utilities suite accessible from the sidebar, starting with a Bitly-style link shortener (with click analytics/logs) and a QR code generator, designed with abuse prevention and security as first-class concerns.

## Scope

### In scope

- A new `utils` backend module with `ShortLink`, `ShortLinkClick`, and `QrCode` entities.
- A `/utils` frontend page shell reachable from the sidebar, hosting both tools.
- Link shortener: create, list, edit, deactivate, expire, and redirect short links; per-link click logs and aggregate analytics.
- QR generator: generate QR codes from URLs, text, or existing short links; download as SVG or PNG.
- Security hardening: destination validation, malicious-URL blocklist checks, rate limiting, SVG sanitization, optional link expiration and password protection, click-time preview/interstitial.
- Audit logging for all create/update/delete operations on `ShortLink` and `QrCode`.

### Out of scope

- Public/anonymous link creation (creation is authenticated only in this epic).
- Custom branded domains and DNS configuration.
- Bulk CSV import/export of links.
- QR code scanning/decoding (generation only).
- Paid-tier analytics dashboards and marketing campaign attribution.

## Modules and Models

1. **Utils** (new module: `backend/app/modules/utils/`)
   - `ShortLink` (header) - the short code -> destination mapping with lifecycle controls.
   - `ShortLinkClick` (detail/log of `ShortLink`) - immutable click event log.
   - `QrCode` (header) - generated QR code metadata and rendered output reference.
2. **Collaboration & Audit** (existing) - `AuditLog` entries for every state change on `ShortLink` and `QrCode`.

See [`docs/features/UTILS.md`](../../docs/features/UTILS.md) for the full data model, security model, and architecture.

## Sprint Plan

Stories within each sprint are independent and can be worked in parallel.

- **Sprint 1: Foundation (parallel)**
  - `story-01-utils-module-scaffold.md` - scaffold `utils` module, entities, and migrations via `forge.py`.
  - `story-02-frontend-shell-sidebar.md` - add Utils entry to the sidebar and build the `/utils` page shell with tabbed routing.
- **Sprint 2: Features (parallel)**
  - `story-03-link-shortener-with-logs.md` - full link shortener vertical slice: CRUD, slug generation, redirect, and click logging.
  - `story-04-qr-generator.md` - full QR generator vertical slice: generate from URL/text/short link, render, download, history.
- **Sprint 3: Security hardening (parallel)**
  - `story-05-link-security-abuse-prevention.md` - rate limiting, destination blocklist/Safe Browsing checks, expiration enforcement, optional password protection, click-time preview interstitial.
  - `story-06-qr-security-validation.md` - SVG sanitization, input validation, content-security policies, and safe rendering.

### Parallelization rationale

- Sprint 1 splits cleanly along the frontend/backend seam: the backend scaffold and the frontend shell share no files.
- Sprint 2 features are fully independent vertical slices (link shortener vs. QR generator) that only depend on the Sprint 1 contracts.
- Sprint 3 hardens the Sprint 2 features along the same two independent seams, so the two stories never touch the same files.

## Definition of Done

- The sidebar exposes a Utils group linking to the link shortener and QR generator pages.
- Authenticated users can create short links and QR codes; redirects resolve and record a click log entry.
- Every create/update/delete on `ShortLink` and `QrCode` writes an `AuditLog` entry.
- Short-link destinations are validated and checked against a blocklist before going live and on a recurring background scan.
- Link creation and QR generation are rate-limited per user.
- QR SVG output is sanitized before rendering; no `javascript:`/`data:` URIs are accepted as QR or short-link input.
- `forge sync` completes with zero errors and migrations apply cleanly.
- All acceptance criteria in the linked stories pass.

## References

- [`docs/features/UTILS.md`](../../docs/features/UTILS.md)
- `docs/erd/ERD.md`
- `docs/architecture/ARCHITECTURE.md`
- `epics/DEVIN.md`
- `epics/07-14-26-foundation-modules/README.md`
