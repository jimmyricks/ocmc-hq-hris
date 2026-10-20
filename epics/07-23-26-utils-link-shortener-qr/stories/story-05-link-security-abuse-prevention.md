---
date_created: 2026-07-23
date_modified: 2026-07-23
title: "US-05: Link Security and Abuse Prevention"
description: Rate limiting, destination blocklist/Safe Browsing checks, expiration, password protection, and click-time preview interstitial.
sprint: 3
points: 8
---

# US-05: Link Security and Abuse Prevention

## Story

As a **platform owner**, I want to **prevent the link shortener from being abused for phishing, malware, and mass redirect attacks** so that **the brand and end users are protected**.

## Acceptance Criteria

- **GIVEN** a user creates short links, **WHEN** they exceed the per-user creation rate limit, **THEN** the API returns 429 Too Many Requests with a Retry-After header and writes an `AuditLog` entry.
- **GIVEN** a destination URL is submitted, **WHEN** it is checked against a malicious-domain blocklist (and Google Safe Browsing v4 where configured), **THEN** links scoring above the block threshold are rejected before going live.
- **GIVEN** a link was created, **WHEN** a recurring background scan flags its destination as newly malicious, **THEN** the link is auto-deactivated and an `AuditLog`/`Notification` is generated for the owner.
- **GIVEN** a link has `expires_at` set, **WHEN** a redirect is requested after expiry, **THEN** the API returns 410 Gone and does not redirect.
- **GIVEN** a link has a password, **WHEN** a redirect is requested without the correct password, **THEN** the API returns a password challenge/interstitial instead of redirecting.
- **GIVEN** the platform enables the preview interstitial, **WHEN** a redirect is requested, **THEN** the user sees the destination URL and a click-through warning before being forwarded (configurable per link or globally).
- **GIVEN** any redirect, **WHEN** it is served, **THEN** the response sets a `Referrer-Policy: no-referrer` and appropriate `Content-Security-Policy` headers on interstitial pages to prevent clickjacking.

## Models

- `ShortLink` (adds `password_hash`, enforces `expires_at`)
- `AuditLog`, `Notification` (side effects)

## Implementation Notes

- Apply progressive per-user throttling on link creation; consider per-IP limits on the public redirect endpoint to blunt brute-force/scan traffic.
- Run destination checks at creation time AND via a scheduled background scan, since URLs can be clean at creation and added to blocklists later.
- Block risky destination patterns: open-redirect endpoints, excessive obfuscation/encoding, newly registered domains (where detectable), `javascript:`/`data:` URIs.
- Store only a hash of any link password; never log it. Use a constant-time comparison.
- Log only necessary routing metadata in `ShortLinkClick`; redact sensitive query parameters.
- This story touches the link create/redirect paths from `story-03` only and shares no files with `story-06-qr-security-validation.md`.

## Dependencies

- `story-03-link-shortener-with-logs.md` (the create and redirect paths to harden).

## Related Stories

- `story-06-qr-security-validation.md` (parallel, QR-side hardening).
