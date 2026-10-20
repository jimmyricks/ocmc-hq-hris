---
date_created: 2026-07-14
date_modified: 2026-07-23
title: Documentation Index
description: Table of contents for the OC HQ project and HRIS documentation
---

# Documentation Index

Use this index to find the right document for your question.

| If you are looking for...                                     | Read this                                                      |
| ------------------------------------------------------------- | -------------------------------------------------------------- |
| What documentation exists and where to start                  | This file                                                      |
| How AI agents should write documentation for this project     | [`DEVIN.md`](DEVIN.md)                                         |
| Core modules, concepts, and high-level architecture           | [`architecture/ARCHITECTURE.md`](architecture/ARCHITECTURE.md) |
| Database entities, relationships, and constraints             | [`erd/ERD.md`](erd/ERD.md)                                     |
| Payroll, task rates, verification workflows, and HR processes | [`hris/HRIS.md`](hris/HRIS.md)                                 |
| Quick employee-to-payroll user journey                        | [`../epics/user-journey.md`](../epics/user-journey.md)         |
| Utils feature design (link shortener, QR generator)           | [`features/UTILS.md`](features/UTILS.md)                       |
| Workspace assistant setup and tool boundaries                 | [`features/ASSISTANT.md`](features/ASSISTANT.md)               |
| How to write epics, stories, and sprints                      | [`../epics/DEVIN.md`](../epics/DEVIN.md)                       |
| Current epics and feature backlog                             | [`../epics/README.md`](../epics/README.md)                     |

## Directory Map

```
docs/
├── INDEX.md              <- you are here
├── DEVIN.md              <- AI documentation style guide
├── architecture/
│   └── ARCHITECTURE.md   <- system design and modules
├── erd/
│   └── ERD.md            <- data model and entity relationships
├── features/
│   └── UTILS.md          <- link shortener and QR generator design
└── hris/
    └── HRIS.md           <- HRIS and payroll design

epics/
├── DEVIN.md              <- epic and story writing guide
├── README.md             <- feature epics and backlog
├── 07-14-26-foundation-modules/       <- core data models
├── 07-14-26-project-task-management/  <- projects and task lifecycle
├── 07-14-26-work-submission/            <- work submissions with external link
├── 07-14-26-hr-verification-approval/ <- submission review and approval
├── 07-14-26-payroll-automation/       <- payroll generation and payment
├── 07-14-26-audit-ledger/             <- audit and ledger reporting
└── 07-23-26-utils-link-shortener-qr/  <- link shortener and QR generator
```
