---
date: 2026-07-23
title: Realignment Implementation Tracker
---

# Realignment Implementation Tracker

Started: 2026-07-23

## Tasks

1. [x] **Generic entity API contract**
   - Status: Completed (2026-07-23)
   - Notes: Added comprehensive tests in `backend/tests/api/test_generic_entity_api_20260723.py`. All 7 tests pass against the generic entity endpoints (`/api/meta`, `/api/entity/{name}/list`, `/api/entity/{name}/detail/{id}`, `/api/entity/{name}/action`, `DELETE /api/entity/{name}/{id}`). Run with `TEST_DATABASE_URL=sqlite+aiosqlite:///./test_contract.db pytest tests/api/test_generic_entity_api_20260723.py -v`.
2. [x] **Project/Task real API**
   - Status: Completed (2026-07-23)
   - Notes: Backend entities and models now match the real API (`project.color/icon`, `task.category_id`, `task_category`, `task_link`). Tests pass (`backend/tests/api/test_project_task_api_20260723.py` 8/8). Frontend `task-manager` `types.ts`, `data.ts`, `utils.ts`, `task-table.svelte`, `task-modal.svelte`, `task-sidebar.svelte`, `nav-projects.svelte`, `store.ts`, and `project/[id]/+page.svelte` rewritten to use backend field names with no mapping. `pnpm check` is clean (0 errors); remaining warnings are unrelated `workflow/[id]` a11y labels and a Svelte state-reference hint. Run tests with `TEST_DATABASE_URL=sqlite+aiosqlite:///./test_final.db pytest tests/api/test_generic_entity_api_20260723.py tests/api/test_project_task_api_20260723.py -v`.
3. [x] **Work Submission + HR Approval flow**
   - Status: Completed (2026-07-24)
   - Notes: Backend `CreateSubmissionRequest` accepts `external_link`; frontend `taskApi` helpers for submissions/approvals; `/submissions` review page for approve/reject/needs_revision; `/tasks/my` submit work dialog with revision chaining.
4. [x] **Payroll Automation**
   - Status: Completed (2026-07-24)
   - Notes: Backend payroll period/entry/line-item services and endpoints tested; frontend `/payroll` page created and wired in sidebar for period creation, generation, approval, and payment.
5. [x] **Audit & Ledger views**
   - Status: Completed (2026-07-24)
   - Notes: Backend `/api/audit-ledger/audit-logs` and `/api/audit-ledger/ledger` endpoints already provide filtered reporting; frontend `/audit` page created with tabbed Audit Logs and Ledger views, search filters, and ledger summary; Audit menu added to sidebar.

## Closure Verification (2026-07-24)

All five realignment tasks were re-verified against the backend and frontend before closing the epics.

- **Backend tests run:** `tests/api/test_generic_entity_api_20260723.py` (7/7 pass), `tests/api/test_project_task_api_20260723.py` (8/8 pass), `tests/epics/test_epic_workflow.py` (9/9 pass). Total: 24/24 passing.
- **`tests/epics/test_epic_workflow.py`** covers the cross-epic lifecycle: assignment deactivation + `in_progress` transition, non-assignee submission rejection, submission versioning, revision chain, approval with `Ledger` credit + notification, rejection returning task to `in_progress`, payroll generation excluding unapproved submissions, payroll payment with `Ledger` debit, and `AuditLog`/`Ledger` immutability via the generic entity API.
- **Frontend pages verified present and wired:** `/admin` (users), `/project/[id]`, `/tasks/my` (submit-for-review dialog), `/submissions` (approve/reject/needs_revision), `/payroll` (period/entry lifecycle), `/audit` (audit logs + ledger). Sidebar links for Payroll and Audit confirmed.
- **Backend modules verified:** `identity_hr`, `project_tasks`, `payroll`, `collaboration_audit` each have `entities/` JSON metadata, `models/` SQLAlchemy models, and (where applicable) `services.py` domain services. API routers live under `backend/app/api/app/` (`project_tasks.py`, `payroll.py`, `audit_ledger.py`).

All six epics and all nine stories are now marked **CLOSED**:

| Epic                              | Story                                | Status |
| --------------------------------- | ------------------------------------ | ------ |
| 07-14-26-foundation-modules       | story-01-identity                    | CLOSED |
| 07-14-26-foundation-modules       | story-02-project-tasks               | CLOSED |
| 07-14-26-foundation-modules       | story-03-payroll                     | CLOSED |
| 07-14-26-foundation-modules       | story-04-collaboration-audit         | CLOSED |
| 07-14-26-project-task-management  | story-01-project-and-task-management | CLOSED |
| 07-14-26-work-submission          | story-01-work-submission             | CLOSED |
| 07-14-26-hr-verification-approval | story-01-hr-verification-approval    | CLOSED |
| 07-14-26-payroll-automation       | story-01-payroll-automation          | CLOSED |
| 07-14-26-audit-ledger             | story-01-audit-ledger                | CLOSED |
