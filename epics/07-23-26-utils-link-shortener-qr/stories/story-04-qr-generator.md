---
date_created: 2026-07-23
date_modified: 2026-07-23
title: "US-04: QR Code Generator"
description: Full vertical slice for generating QR codes from URL, text, or short links and downloading them.
sprint: 2
points: 5
---

# US-04: QR Code Generator

## Story

As an **authenticated user**, I want to **generate QR codes from a URL, text, or one of my short links and download them as SVG or PNG** so that **I can share scannable codes for print and screen**.

## Acceptance Criteria

- **GIVEN** I am authenticated and on `/utils/qr`, **WHEN** I enter a URL or text and choose error-correction level (L/M/Q/H), size, format (SVG/PNG), and colors, **THEN** the API (or client) generates a QR code and renders it in the page.
- **GIVEN** I have short links, **WHEN** I pick one as the source, **THEN** the QR encodes the short URL and the `QrCode` record stores `short_link_id`.
- **GIVEN** a generated QR code, **WHEN** I click download, **THEN** I receive an SVG or PNG file with the chosen parameters.
- **GIVEN** I generate a QR code, **WHEN** the generation completes, **THEN** a `QrCode` record is stored (source type/value, parameters, format, `created_by`) and an `AuditLog` entry is written.
- **GIVEN** I open the QR history view, **WHEN** the page loads, **THEN** I see my previously generated QR codes scoped to my account (admins see all) and can re-render or download them.
- **GIVEN** a QR input, **WHEN** the input is a `javascript:` or `data:` URI, **THEN** generation is rejected with a validation error.

## Models

- `QrCode`
- `AuditLog` (side effect)

## Implementation Notes

- Use an established QR library (e.g. `qrcode` on the backend, or a vetted client-side library). Do not hand-build encoding logic.
- Prefer SVG output for web embedding (scalable, small); offer PNG for download/print.
- Respect quiet zones and contrast; default error correction to `M` for screen, document `H` for print.
- Keep the `QrCode` record storing parameters (not the rendered bytes) so codes can be regenerated deterministically; store rendered output in object storage only if caching is needed.
- This story is independent of `story-03-link-shortener-with-logs.md` except for the optional `short_link_id` link, which can be wired after both land.

## Dependencies

- `story-01-utils-module-scaffold.md` (the `QrCode` entity and migration).
- `story-02-frontend-shell-sidebar.md` (the `/utils/qr` route placeholder).

## Related Stories

- `story-06-qr-security-validation.md` hardens rendering and validation built here.
- `story-03-link-shortener-with-logs.md` provides the optional `short_link_id` source.
