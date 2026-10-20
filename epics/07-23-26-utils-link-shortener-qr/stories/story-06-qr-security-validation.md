---
date_created: 2026-07-23
date_modified: 2026-07-23
title: "US-06: QR Security and Validation"
description: SVG sanitization, input validation, and content-security policies for safe QR rendering and download.
sprint: 3
points: 5
---

# US-06: QR Security and Validation

## Story

As a **platform owner**, I want to **ensure generated QR codes cannot be used to deliver XSS or malicious payloads** so that **users and downstream consumers are protected**.

## Acceptance Criteria

- **GIVEN** a QR code is rendered as SVG, **WHEN** the SVG is produced, **THEN** it is sanitized (e.g. via DOMPurify with the SVG profile) to strip `<script>`, event handlers, and disallowed elements/attributes before being inserted into the DOM.
- **GIVEN** a QR input, **WHEN** it is a `javascript:`, `data:`, `vbscript:`, or other disallowed URI scheme, **THEN** generation is rejected with a validation error.
- **GIVEN** a QR code is served for download, **WHEN** the response is sent, **THEN** it sets the correct `Content-Type` (`image/svg+xml` or `image/png`) and a `Content-Disposition: attachment` to prevent inline execution, and SVG downloads are served with `Content-Security-Policy: default-src 'none'`.
- **GIVEN** a QR code is embedded in the page, **WHEN** it renders, **THEN** it uses an allowlist of SVG elements (`svg`, `path`, `rect`, `g`, `polygon`, `line`) and blocks all `on*` handlers and external references.
- **GIVEN** a user generates QR codes, **WHEN** they exceed the per-user rate limit, **THEN** the API returns 429 Too Many Requests.
- **GIVEN** a generated QR is stored, **WHEN** it is re-rendered from history, **THEN** the same sanitization and validation is applied (never trust stored rendered output over re-sanitizing).

## Models

- `QrCode` (validation only; no schema change required)

## Implementation Notes

- Prefer rendering QR codes via a component or canvas rather than `dangerouslySetInnerHTML`/`@html` of raw SVG; if raw SVG must be used, always sanitize first.
- Validate and normalize input server-side regardless of client validation (defense in depth).
- Constrain QR input length and character set to library-supported limits to avoid encoder edge cases.
- Apply rate limiting consistent with `story-05` (reuse the same throttle mechanism).
- This story touches the QR generate/render paths from `story-04` only and shares no files with `story-05-link-security-abuse-prevention.md`.

## Dependencies

- `story-04-qr-generator.md` (the generate and render paths to harden).

## Related Stories

- `story-05-link-security-abuse-prevention.md` (parallel, link-side hardening).
