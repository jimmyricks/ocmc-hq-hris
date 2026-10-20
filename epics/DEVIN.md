---
date_created: 2026-07-14
date_modified: 2026-07-14
title: Epic and Story Writing Guide
description: How to write epics, user stories, and sprints for the OC HQ project
---

# Epic and Story Writing Guide

This guide defines the standard format for epics, user stories, and sprint plans in `epics/`. All planning artifacts are markdown files and follow the same frontmatter and style rules as the rest of `docs/`.

## Epic Format

An epic is a folder named with the date it is created (`mm-dd-yy`) and a short kebab-case title.

```
epics/
├── README.md
├── DEVIN.md                          <- this file
└── 07-14-26-foundation-modules/      <- example epic folder
    ├── README.md                     <- epic overview and acceptance criteria
    └── stories/                      <- user stories
        ├── story-01-identity.md
        ├── story-02-project-tasks.md
        └── ...
```

### Epic Folder Naming

Use the pattern: `mm-dd-yy-{short-title}`.

- Date is the day the epic is created in `mm-dd-yy` format.
- Slashes are replaced with dashes because file systems cannot contain `/`.
- Keep the title short, kebab-case, and descriptive.

### Epic README.md

Every epic folder must contain an `README.md` with:

1. Required frontmatter.
2. **Goal** — one sentence describing the business outcome.
3. **Scope** — what is in and out of the epic.
4. **Modules and Models** — list of modules and entities impacted.
5. **Sprint Plan** — summary of sprints and which stories belong to each.
6. **Definition of Done** — acceptance criteria for the whole epic.
7. **References** — links to `docs/erd/ERD.md`, `docs/architecture/ARCHITECTURE.md`, and any other relevant docs.

## User Story Format

Each user story is a markdown file inside the epic's `stories/` folder.

### File Naming

Use: `story-{nn}-{short-title}.md`

- `nn` is a zero-padded sequence number.
- The title is kebab-case and matches the story's subject.

### Story Structure

```markdown
---
date_created: 2026-07-14
date_modified: 2026-07-14
title: "US-01: Manage Users"
description: Admin can create and manage user accounts
sprint: 1
points: 5
---

# US-01: Manage Users

## Story

As an **admin**, I want to **create and manage user accounts** so that **users, project managers, and HR can log in with the correct roles**.

## Acceptance Criteria

- **GIVEN** I am an admin, **WHEN** I create a user with email and role, **THEN** the user is saved with a hashed password and active status.
- **GIVEN** a user exists, **WHEN** I update their role or status, **THEN** an `AuditLog` entry is written.

## Models

- `User`

## Related Stories

- `story-02-department.md` depends on this story for `head_user_id`.

## Notes

- Use `forge.py` to generate `User` metadata and model.
- Business logic lives in `modules/identity_hr/entities/User.py`.
```

## Writing Rules

1. **One idea per story** — a story should describe a single, testable capability.
2. **Parallel stories** — stories within the same sprint should be independent enough to be worked on in parallel. If one story depends on another, place it in a later sprint or call out the dependency explicitly.
3. **Reference, do not duplicate** — link to `docs/erd/ERD.md` for model details. Do not copy full entity tables into stories.
4. **Include audit and ledger** — any story that changes state or money must mention `AuditLog`, `Ledger`, or `Notification` side effects.
5. **No emojis** — use plain text.
6. **Frontmatter on every file** — `date_created`, `date_modified`, `title`, `description`.
7. **Update `date_modified`** on every edit.

## Sprint Plan Format

Sprints are documented in the epic `README.md` and optionally in `sprint-{nn}.md` files.

A sprint plan contains:

1. **Sprint goal** — one sentence.
2. **Stories** — list of story files in the sprint.
3. **Dependencies** — external dependencies or prerequisites.
4. **Definition of done** — what must be true for the sprint to be considered complete.

### Sprint Naming

Use `Sprint 1`, `Sprint 2`, etc. Story files reference the sprint number in their frontmatter.

### Parallelization

- Stories in the same sprint must be independent enough to be worked on in parallel.
- If a natural dependency exists, the downstream story goes into a later sprint.
- Shared interfaces, base classes, or stubs should be completed in Sprint 1.

## Architecture and Compliance

- All models must align with `docs/erd/ERD.md` and `docs/architecture/ARCHITECTURE.md`.
- Use `modules/<module>/<entities>/<Entity>.py` for business logic.
- Use `forge.py` for scaffolding; do not hand-write model boilerplate.
- Follow DRY and SOLID:
  - One entity per file.
  - Extend behavior through composition, not by modifying stable core code.
  - Depend on abstractions, not concrete frameworks.
- Every state change writes to `AuditLog`; every financial change writes to `Ledger`.

## Maintenance

- Add new epics to `epics/README.md`.
- Update `docs/INDEX.md` if a new epic or guide is referenced.
- Archive completed epics by moving them to `epics/archive/`.
