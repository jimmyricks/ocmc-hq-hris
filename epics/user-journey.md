---
date: 2026-10-20
title: OCMC HQ User Journey
---

# OCMC HQ: User Journey

## Roles

- **Employee:** works assigned tasks, comments, submits work, checks pay.
- **Project Manager:** manages projects and members, assigns tasks, reviews submissions.
- **HR:** configures rates, generates payroll, approves and pays entries.
- **Administrator:** manages users, roles, permissions, and workflows.

## End-to-End Flow

1. **Sign in** — User authenticates and lands in the workspace. API actions are checked against assigned roles and permissions.
2. **Set up work** — A PM creates a project, adds members, creates tasks, and assigns an employee. Assignment moves a pending task to in progress and creates an in-app notification; the dedicated assignment endpoint also queues an email to the assignee.
3. **Do the work** — Employee opens My Tasks, uses the task details and comments thread, then submits notes or a work link. The submission is versioned, the task moves to for review, and the project manager receives an in-app notification.
4. **Review** — PM approves, rejects, or requests revisions. Rejected work returns to in progress; revision requests require remarks. Approval records the decision, credits the employee ledger, and notifies the employee.
5. **Run payroll** — HR creates a date-range period and generates payroll from approved submissions in that period. The system groups line items by employee, applies each task type's rate, totals entries, and closes approved tasks.
6. **Approve and pay** — HR approves and pays each entry. Payment creates an invoice and ledger debit, and notifies the employee. A period is marked paid only after all its entries are paid.

## Work States

```text
Pending --assignment--> In Progress --submit--> For Review
   ^                                          /       |
   |                                  reject /        | approve
   +----------------------------------------+         v
                                                Approved --payroll--> Closed

For Review --request revision--> Needs Revision --resubmit--> For Review
```

## Useful Workspace Areas

- **Overview:** personal workload, reviews, due dates, and project progress.
- **Planner:** project-filtered due-date calendar and agenda.
- **Projects / My Tasks:** task boards, assignments, submissions, and task comments.
- **Payroll / Task Rates:** employee compensation and HR approval/payment workflow.
- **Creator tools:** QR generation and link shortening.
- **Administration:** users, roles, permissions, and workflow configuration.

## Key API Paths

- Auth: `POST /api/auth/login`, `GET /api/profile`
- Projects and members: generic `/api/entity/{entity}` endpoints
- Task creation and assignment: `POST /api/project-tasks/tasks`, `POST /api/project-tasks/tasks/{id}/assign`
- Submit and review: `POST /api/project-tasks/submissions`, `POST /api/project-tasks/submissions/{id}/approve`
- Payroll: `POST /api/payroll/periods`, `POST /api/payroll/periods/generate`, `/api/payroll/entries/{id}/approve`, `/api/payroll/entries/{id}/pay`
- Comments: `/api/features/comments/task/{task_id}`

## Important Rules

- Only the assigned employee (or a superuser) may submit work for an active assignment.
- Reassigning a task deactivates its previous active assignment.
- Only approved submissions within the payroll period are included in generated payroll.
- Regeneration is allowed while entries are drafts; it is blocked once an entry has been approved or paid.
- Task assignment email delivery is best-effort: SMTP failures are logged and do not undo the assignment.
