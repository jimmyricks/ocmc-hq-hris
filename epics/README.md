---
date_created: 2026-07-14
date_modified: 2026-07-23
title: Epics and Backlog
description: Product epics and feature backlog for OC HQ
---

# Epics and Backlog

This folder contains product-level epics and feature backlogs.

## Active Epics

1. **[07-23-26 Utils - Link Shortener and QR Generator](07-23-26-utils-link-shortener-qr/README.md)** — self-hosted Bitly-style link shortener with click logs and a QR code generator, exposed under a Utils sidebar page. Design: [`docs/features/UTILS.md`](../docs/features/UTILS.md).

## Completed Epics

1. **[07-14-26 Foundation - Core Modules and Data Models](07-14-26-foundation-modules/README.md)** — scaffold all modules and entities from `docs/erd/ERD.md` v3.
2. **[07-14-26 Project & Task Management](07-14-26-project-task-management/README.md)** — create projects, assign tasks, track statuses.
3. **[07-14-26 Work Submission](07-14-26-work-submission/README.md)** — users submit tasks with an external deliverable link.
4. **[07-14-26 HR Verification & Approval](07-14-26-hr-verification-approval/README.md)** — HR and admin review and approve submissions.
5. **[07-14-26 Payroll Automation](07-14-26-payroll-automation/README.md)** — bi-monthly payroll calculation based on approved tasks.
6. **[07-14-26 Audit & Ledger](07-14-26-audit-ledger/README.md)** — immutable audit logs and financial ledgers.

## How to Add an Epic

1. Read [`DEVIN.md`](DEVIN.md) for the epic and story format.
2. Create a folder named `mm-dd-yy-{short-title}`.
3. Add an `README.md` and the user stories inside the `stories/` folder.
4. Update this file and `docs/INDEX.md`.
