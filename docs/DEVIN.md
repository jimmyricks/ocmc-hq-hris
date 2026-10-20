---
date_created: 2026-07-14
date_modified: 2026-07-14
title: AI Documentation Style Guide
description: Instructions for AI agents writing documentation for the OC HQ project
---

# AI Documentation Style Guide

This guide ensures all project documentation and code are consistent, discoverable, and maintainable.

## Required Frontmatter

Every markdown file must start with:

```yaml
---
date_created: YYYY-MM-DD
date_modified: YYYY-MM-DD
title: Short Title
description: Optional one-line summary
---
```

Update `date_modified` every time a file is edited.

## File Organization

- Keep the `docs/` directory clean by placing related documents in subdirectories.
- Use `docs/INDEX.md` as the single table of contents.
- Use `epics/` for product-level feature epics and backlog items.
- Do not duplicate content; link to the source document instead.

## Directory Layout

```
docs/
├── INDEX.md
├── DEVIN.md
├── architecture/
├── erd/
└── hris/

epics/
```

## Writing Rules

1. **Use Markdown** with clear headings.
2. **Be concise**; avoid unnecessary explanations.
3. **Use Mermaid** for ERD, architecture, and workflow diagrams.
4. **Define data models** in tables with field, type, and description columns.
5. **Include audit and ledger** considerations for any model that tracks state or money.
6. **No emojis** unless explicitly requested.
7. **No redundant copies** of the same information.

## Code Architecture Standards

### Clean + Hybrid Architecture

- Keep system functionality (framework, delivery, infrastructure, persistence) clean and separated.
- All **business logic** must live in `modules/<module>/<entities>/` (for example, `modules/project/tasks/Task.py`).
- Follow the Frappe-like pattern: every metadata file (`*.json`) and client script (`*.js`) has a corresponding Python entity file (`*.py`) that owns its domain behavior.
- Use cases / services may orchestrate entities, but they should not contain entity-specific business rules.
- Repositories and adapters handle persistence; domain code depends on abstractions, not concrete frameworks.

### DRY + SOLID

- **DRY** — do not duplicate validation rules, metadata, constants, or business logic.
- **Single Responsibility** — one class/file per entity behavior.
- **Open/Closed** — extend behavior through composition/inheritance, not by modifying stable core code.
- **Liskov Substitution** — derived entity classes must be usable wherever the base is expected.
- **Interface Segregation** — keep small, focused interfaces for repositories and services.
- **Dependency Inversion** — depend on abstractions (interfaces, protocols) rather than concrete implementations.

### Anti-Patterns to Avoid

- Hardcoding business logic in views, controllers, or route handlers.
- Duplicating validation, permissions, or state-machine rules across the stack.
- Magic strings, hard-coded IDs, or ad-hoc conditionals for entity behavior.
- Monolithic files that mix multiple entities or concerns.
- Direct database access from UI or API layers.
- Skipping `AuditLog` or `Ledger` for state/financial changes.
- Mixing framework code with domain logic.
- Writing boilerplate by hand when `forge.py` can generate it.

## forge.py Tooling

- Use `forge.py` as the primary toolkit for creating models and `metadata.json` files.
- Do not hand-write model boilerplate, JSON schemas, or migration stubs if `forge.py` can generate them.
- Keep `metadata.json` as the source of truth for entity definitions.
- When `forge.py` is used, verify the generated output and commit both `metadata.json` and the generated code.
- For custom behavior, extend the generated entity in the `modules/<module>/<entities>/<Entity>.py` file.

## Maintenance

- Add new documents to `docs/INDEX.md`.
- Update `date_modified` on every change.
- Archive or delete obsolete documents rather than leaving stale copies.
