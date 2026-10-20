-- Seed script for payroll test data
-- Creates: 3 workers, task types, tasks, approved submissions,
--           3 payroll periods (draft / approved / paid) with entries + line items,
--           and payroll settings.
-- Run with: psql -d oc_hq -f scripts/seed_payroll_test_data.sql

BEGIN;

-- ── Workers ──────────────────────────────────────────────────────────
-- Reuse admin's password hash for all test users
INSERT INTO core_users (id, username, email, full_name, first_name, last_name, hashed_password, is_active, is_superuser, created_at, updated_at)
VALUES
  ('wkr-0001-aaaa-bbbb-cccc-000000000001', 'jane.smith',    'jane.smith@example.com',    'Jane Smith',    'Jane', 'Smith',    '$2b$12$6176iZZUWpaKhHxlCw4Fi..9JqRmxYrKoEtMuuwGQaLCZd6hQNIHO', true, false, NOW(), NOW()),
  ('wkr-0002-aaaa-bbbb-cccc-000000000002', 'carlos.mendez', 'carlos.mendez@example.com', 'Carlos Mendez', 'Carlos','Mendez', '$2b$12$6176iZZUWpaKhHxlCw4Fi..9JqRmxYrKoEtMuuwGQaLCZd6hQNIHO', true, false, NOW(), NOW()),
  ('wkr-0003-aaaa-bbbb-cccc-000000000003', 'aria.lee',      'aria.lee@example.com',      'Aria Lee',      'Aria', 'Lee',      '$2b$12$6176iZZUWpaKhHxlCw4Fi..9JqRmxYrKoEtMuuwGQaLCZd6hQNIHO', true, false, NOW(), NOW())
ON CONFLICT (username) DO NOTHING;

-- Assign Technician role to workers
INSERT INTO core_user_roles (user_id, role_id)
SELECT u.id, '8186866e-74aa-423b-8bf8-16297232bd92'
FROM core_users u
WHERE u.username IN ('jane.smith', 'carlos.mendez', 'aria.lee')
ON CONFLICT DO NOTHING;

-- ── Task Types (with different rates) ────────────────────────────────
INSERT INTO task_type (id, name, description, unit_rate, unit, requires_approval, created_by, created_at, updated_at)
VALUES
  ('TYP-00002', 'Development',     'Coding & implementation tasks', 75.00,  'per_hour',  true,  'cc6ba2c0-7e0d-404d-a0e3-345ea178cb08', NOW(), NOW()),
  ('TYP-00003', 'Design',          'UI/UX design tasks',            60.00,  'per_hour',  true,  'cc6ba2c0-7e0d-404d-a0e3-345ea178cb08', NOW(), NOW()),
  ('TYP-00004', 'Data Entry',      'Data entry & encoding',         20.00,  'per_task',  false, 'cc6ba2c0-7e0d-404d-a0e3-345ea178cb08', NOW(), NOW()),
  ('TYP-00005', 'Quality Review',  'QA & review tasks',             40.00,  'per_task',  true,  'cc6ba2c0-7e0d-404d-a0e3-345ea178cb08', NOW(), NOW())
ON CONFLICT (id) DO NOTHING;

-- Update series counter for TYP
INSERT INTO series (name, current) VALUES ('TYP', 5)
ON CONFLICT (name) DO UPDATE SET current = GREATEST(series.current, 5);

-- ── Tasks (approved/closed for payroll) ──────────────────────────────
-- Period 3 (June 1-15, paid): 3 tasks, all closed
INSERT INTO task (id, project_id, task_type_id, title, description, priority, status, due_date, created_by, created_at, updated_at)
VALUES
  ('TASK-00010', 'PRJ-00001', 'TYP-00001', 'Write API docs (June 1)',   'API documentation for v1',     'medium', 'closed', '2026-06-05', 'cc6ba2c0-7e0d-404d-a0e3-345ea178cb08', '2026-06-01', '2026-06-10'),
  ('TASK-00011', 'PRJ-00001', 'TYP-00002', 'Build login page (June 1)', 'Implement login UI',           'high',   'closed', '2026-06-08', 'cc6ba2c0-7e0d-404d-a0e3-345ea178cb08', '2026-06-01', '2026-06-12'),
  ('TASK-00012', 'PRJ-00001', 'TYP-00003', 'Design dashboard (June 1)', 'Dashboard mockup',             'medium', 'closed', '2026-06-10', 'cc6ba2c0-7e0d-404d-a0e3-345ea178cb08', '2026-06-01', '2026-06-14')
ON CONFLICT (id) DO NOTHING;

-- Period 2 (June 16-30, approved): 3 tasks, all closed
INSERT INTO task (id, project_id, task_type_id, title, description, priority, status, due_date, created_by, created_at, updated_at)
VALUES
  ('TASK-00020', 'PRJ-00001', 'TYP-00002', 'Fix auth bug (June 16)',     'Fix token refresh bug',        'high',   'closed', '2026-06-20', 'cc6ba2c0-7e0d-404d-a0e3-345ea178cb08', '2026-06-16', '2026-06-22'),
  ('TASK-00021', 'PRJ-00001', 'TYP-00004', 'Data migration (June 16)',   'Migrate legacy data',          'low',    'closed', '2026-06-25', 'cc6ba2c0-7e0d-404d-a0e3-345ea178cb08', '2026-06-16', '2026-06-28'),
  ('TASK-00022', 'PRJ-00001', 'TYP-00005', 'QA review (June 16)',        'Review v1.2 release',          'medium', 'closed', '2026-06-28', 'cc6ba2c0-7e0d-404d-a0e3-345ea178cb08', '2026-06-16', '2026-06-30')
ON CONFLICT (id) DO NOTHING;

-- Period 1 (July 1-15, draft): 3 tasks, approved (will be closed by payroll gen)
INSERT INTO task (id, project_id, task_type_id, title, description, priority, status, due_date, created_by, created_at, updated_at)
VALUES
  ('TASK-00030', 'PRJ-00001', 'TYP-00001', 'Write release notes (July)',  'Release notes for v1.3',       'low',    'approved', '2026-07-10', 'cc6ba2c0-7e0d-404d-a0e3-345ea178cb08', '2026-07-01', '2026-07-08'),
  ('TASK-00031', 'PRJ-00001', 'TYP-00002', 'Add export feature (July)',   'CSV export endpoint',          'medium', 'approved', '2026-07-12', 'cc6ba2c0-7e0d-404d-a0e3-345ea178cb08', '2026-07-01', '2026-07-10'),
  ('TASK-00032', 'PRJ-00001', 'TYP-00003', 'Redesign sidebar (July)',     'Sidebar UX improvements',      'medium', 'approved', '2026-07-14', 'cc6ba2c0-7e0d-404d-a0e3-345ea178cb08', '2026-07-01', '2026-07-12')
ON CONFLICT (id) DO NOTHING;

-- Update TASK series
INSERT INTO series (name, current) VALUES ('TASK', 32)
ON CONFLICT (name) DO UPDATE SET current = GREATEST(series.current, 32);

-- ── Task Assignments ─────────────────────────────────────────────────
INSERT INTO task_assignment (id, task_id, user_id, is_active, created_by, created_at, updated_at)
VALUES
  -- Period 3 (paid): Jane gets 2 tasks, Carlos gets 1
  ('TAS-00010', 'TASK-00010', 'wkr-0001-aaaa-bbbb-cccc-000000000001', true, 'cc6ba2c0-7e0d-404d-a0e3-345ea178cb08', '2026-06-01', '2026-06-01'),
  ('TAS-00011', 'TASK-00011', 'wkr-0001-aaaa-bbbb-cccc-000000000001', true, 'cc6ba2c0-7e0d-404d-a0e3-345ea178cb08', '2026-06-01', '2026-06-01'),
  ('TAS-00012', 'TASK-00012', 'wkr-0002-aaaa-bbbb-cccc-000000000002', true, 'cc6ba2c0-7e0d-404d-a0e3-345ea178cb08', '2026-06-01', '2026-06-01'),
  -- Period 2 (approved): Carlos gets 2, Aria gets 1
  ('TAS-00020', 'TASK-00020', 'wkr-0002-aaaa-bbbb-cccc-000000000002', true, 'cc6ba2c0-7e0d-404d-a0e3-345ea178cb08', '2026-06-16', '2026-06-16'),
  ('TAS-00021', 'TASK-00021', 'wkr-0002-aaaa-bbbb-cccc-000000000002', true, 'cc6ba2c0-7e0d-404d-a0e3-345ea178cb08', '2026-06-16', '2026-06-16'),
  ('TAS-00022', 'TASK-00022', 'wkr-0003-aaaa-bbbb-cccc-000000000003', true, 'cc6ba2c0-7e0d-404d-a0e3-345ea178cb08', '2026-06-16', '2026-06-16'),
  -- Period 1 (draft): Jane 1, Carlos 1, Aria 1
  ('TAS-00030', 'TASK-00030', 'wkr-0001-aaaa-bbbb-cccc-000000000001', true, 'cc6ba2c0-7e0d-404d-a0e3-345ea178cb08', '2026-07-01', '2026-07-01'),
  ('TAS-00031', 'TASK-00031', 'wkr-0002-aaaa-bbbb-cccc-000000000002', true, 'cc6ba2c0-7e0d-404d-a0e3-345ea178cb08', '2026-07-01', '2026-07-01'),
  ('TAS-00032', 'TASK-00032', 'wkr-0003-aaaa-bbbb-cccc-000000000003', true, 'cc6ba2c0-7e0d-404d-a0e3-345ea178cb08', '2026-07-01', '2026-07-01')
ON CONFLICT (id) DO NOTHING;

-- Update TAS series
INSERT INTO series (name, current) VALUES ('TAS', 32)
ON CONFLICT (name) DO UPDATE SET current = GREATEST(series.current, 32);

-- ── Task Submissions (approved, within period date ranges) ───────────
INSERT INTO task_submission (id, task_assignment_id, version, notes, status, submitted_by, submitted_at, created_by, created_at, updated_at)
VALUES
  -- Period 3 (June 1-15, paid)
  ('SUB-00010', 'TAS-00010', 1, 'API docs complete',     'approved', 'wkr-0001-aaaa-bbbb-cccc-000000000001', '2026-06-08 10:00:00', 'wkr-0001-aaaa-bbbb-cccc-000000000001', '2026-06-08', '2026-06-08'),
  ('SUB-00011', 'TAS-00011', 1, 'Login page done',       'approved', 'wkr-0001-aaaa-bbbb-cccc-000000000001', '2026-06-10 14:00:00', 'wkr-0001-aaaa-bbbb-cccc-000000000001', '2026-06-10', '2026-06-10'),
  ('SUB-00012', 'TAS-00012', 1, 'Dashboard mockup done', 'approved', 'wkr-0002-aaaa-bbbb-cccc-000000000002', '2026-06-12 09:00:00', 'wkr-0002-aaaa-bbbb-cccc-000000000002', '2026-06-12', '2026-06-12'),
  -- Period 2 (June 16-30, approved)
  ('SUB-00020', 'TAS-00020', 1, 'Auth bug fixed',        'approved', 'wkr-0002-aaaa-bbbb-cccc-000000000002', '2026-06-20 11:00:00', 'wkr-0002-aaaa-bbbb-cccc-000000000002', '2026-06-20', '2026-06-20'),
  ('SUB-00021', 'TAS-00021', 1, 'Migration complete',    'approved', 'wkr-0002-aaaa-bbbb-cccc-000000000002', '2026-06-26 15:00:00', 'wkr-0002-aaaa-bbbb-cccc-000000000002', '2026-06-26', '2026-06-26'),
  ('SUB-00022', 'TAS-00022', 1, 'QA review done',        'approved', 'wkr-0003-aaaa-bbbb-cccc-000000000003', '2026-06-28 16:00:00', 'wkr-0003-aaaa-bbbb-cccc-000000000003', '2026-06-28', '2026-06-28'),
  -- Period 1 (July 1-15, draft)
  ('SUB-00030', 'TAS-00030', 1, 'Release notes ready',   'approved', 'wkr-0001-aaaa-bbbb-cccc-000000000001', '2026-07-08 10:00:00', 'wkr-0001-aaaa-bbbb-cccc-000000000001', '2026-07-08', '2026-07-08'),
  ('SUB-00031', 'TAS-00031', 1, 'Export feature done',   'approved', 'wkr-0002-aaaa-bbbb-cccc-000000000002', '2026-07-10 13:00:00', 'wkr-0002-aaaa-bbbb-cccc-000000000002', '2026-07-10', '2026-07-10'),
  ('SUB-00032', 'TAS-00032', 1, 'Sidebar redesigned',    'approved', 'wkr-0003-aaaa-bbbb-cccc-000000000003', '2026-07-12 09:00:00', 'wkr-0003-aaaa-bbbb-cccc-000000000003', '2026-07-12', '2026-07-12')
ON CONFLICT (id) DO NOTHING;

-- ── Payroll Settings (singleton) ─────────────────────────────────────
INSERT INTO payroll_settings (id, currency, cutoff_rule, auto_approve_threshold, require_hr_approval, notify_users_on_payment, default_period_start_day, default_period_end_day, created_by, created_at, updated_at)
VALUES ('PS-00001', 'USD', 'bi_monthly', 500.00, true, true, 1, 15, 'cc6ba2c0-7e0d-404d-a0e3-345ea178cb08', NOW(), NOW())
ON CONFLICT (id) DO NOTHING;

-- ── Payroll Periods ──────────────────────────────────────────────────
-- Period 3: June 1-15 (PAID)
INSERT INTO payroll_period (id, label, period_type, start_date, end_date, cutoff, status, is_auto_generated, created_by, created_at, updated_at)
VALUES ('PP-00003', 'June 1-15, 2026', 'bi_monthly', '2026-06-01', '2026-06-15', '2026-06-15', 'paid', false, 'cc6ba2c0-7e0d-404d-a0e3-345ea178cb08', '2026-06-01', '2026-06-15')
ON CONFLICT (id) DO NOTHING;

-- Period 2: June 16-30 (APPROVED entries, period still open)
INSERT INTO payroll_period (id, label, period_type, start_date, end_date, cutoff, status, is_auto_generated, created_by, created_at, updated_at)
VALUES ('PP-00002', 'June 16-30, 2026', 'bi_monthly', '2026-06-16', '2026-06-30', '2026-06-30', 'open', false, 'cc6ba2c0-7e0d-404d-a0e3-345ea178cb08', '2026-06-16', '2026-06-30')
ON CONFLICT (id) DO NOTHING;

-- Period 1: July 1-15 (DRAFT entries, current period)
INSERT INTO payroll_period (id, label, period_type, start_date, end_date, cutoff, status, is_auto_generated, created_by, created_at, updated_at)
VALUES ('PP-00001', 'July 1-15, 2026', 'bi_monthly', '2026-07-01', '2026-07-15', '2026-07-15', 'open', false, 'cc6ba2c0-7e0d-404d-a0e3-345ea178cb08', '2026-07-01', '2026-07-01')
ON CONFLICT (id) DO NOTHING;

-- ── Payroll Entries + Line Items ─────────────────────────────────────

-- === Period 3 (June 1-15, PAID) ===
-- Jane: 2 tasks (docs $50 + dev $75) = $125
INSERT INTO payroll_entry (id, payroll_period_id, user_id, total_tasks, total_amount, status, generated_at, approved_by, approved_at, created_by, created_at, updated_at)
VALUES ('PE-00031', 'PP-00003', 'wkr-0001-aaaa-bbbb-cccc-000000000001', 2, 125.00, 'paid', '2026-06-15 12:00:00', 'cc6ba2c0-7e0d-404d-a0e3-345ea178cb08', '2026-06-15 14:00:00', 'cc6ba2c0-7e0d-404d-a0e3-345ea178cb08', '2026-06-15', '2026-06-15')
ON CONFLICT (id) DO NOTHING;

INSERT INTO payroll_line_item (id, payroll_entry_id, idx, task_submission_id, rate, quantity, amount, created_by, created_at, updated_at)
VALUES
  ('PLI-00031', 'PE-00031', 1, 'SUB-00010', 50.00, 1, 50.00, 'cc6ba2c0-7e0d-404d-a0e3-345ea178cb08', '2026-06-15', '2026-06-15'),
  ('PLI-00032', 'PE-00031', 2, 'SUB-00011', 75.00, 1, 75.00, 'cc6ba2c0-7e0d-404d-a0e3-345ea178cb08', '2026-06-15', '2026-06-15')
ON CONFLICT (id) DO NOTHING;

-- Carlos: 1 task (design $60) = $60
INSERT INTO payroll_entry (id, payroll_period_id, user_id, total_tasks, total_amount, status, generated_at, approved_by, approved_at, created_by, created_at, updated_at)
VALUES ('PE-00032', 'PP-00003', 'wkr-0002-aaaa-bbbb-cccc-000000000002', 1, 60.00, 'paid', '2026-06-15 12:00:00', 'cc6ba2c0-7e0d-404d-a0e3-345ea178cb08', '2026-06-15 14:00:00', 'cc6ba2c0-7e0d-404d-a0e3-345ea178cb08', '2026-06-15', '2026-06-15')
ON CONFLICT (id) DO NOTHING;

INSERT INTO payroll_line_item (id, payroll_entry_id, idx, task_submission_id, rate, quantity, amount, created_by, created_at, updated_at)
VALUES ('PLI-00033', 'PE-00032', 1, 'SUB-00012', 60.00, 1, 60.00, 'cc6ba2c0-7e0d-404d-a0e3-345ea178cb08', '2026-06-15', '2026-06-15')
ON CONFLICT (id) DO NOTHING;

-- === Period 2 (June 16-30, APPROVED) ===
-- Carlos: 2 tasks (dev $75 + data entry $20) = $95
INSERT INTO payroll_entry (id, payroll_period_id, user_id, total_tasks, total_amount, status, generated_at, approved_by, approved_at, created_by, created_at, updated_at)
VALUES ('PE-00021', 'PP-00002', 'wkr-0002-aaaa-bbbb-cccc-000000000002', 2, 95.00, 'approved', '2026-06-30 12:00:00', 'cc6ba2c0-7e0d-404d-a0e3-345ea178cb08', '2026-06-30 14:00:00', 'cc6ba2c0-7e0d-404d-a0e3-345ea178cb08', '2026-06-30', '2026-06-30')
ON CONFLICT (id) DO NOTHING;

INSERT INTO payroll_line_item (id, payroll_entry_id, idx, task_submission_id, rate, quantity, amount, created_by, created_at, updated_at)
VALUES
  ('PLI-00021', 'PE-00021', 1, 'SUB-00020', 75.00, 1, 75.00, 'cc6ba2c0-7e0d-404d-a0e3-345ea178cb08', '2026-06-30', '2026-06-30'),
  ('PLI-00022', 'PE-00021', 2, 'SUB-00021', 20.00, 1, 20.00, 'cc6ba2c0-7e0d-404d-a0e3-345ea178cb08', '2026-06-30', '2026-06-30')
ON CONFLICT (id) DO NOTHING;

-- Aria: 1 task (QA $40) = $40
INSERT INTO payroll_entry (id, payroll_period_id, user_id, total_tasks, total_amount, status, generated_at, approved_by, approved_at, created_by, created_at, updated_at)
VALUES ('PE-00022', 'PP-00002', 'wkr-0003-aaaa-bbbb-cccc-000000000003', 1, 40.00, 'approved', '2026-06-30 12:00:00', 'cc6ba2c0-7e0d-404d-a0e3-345ea178cb08', '2026-06-30 14:00:00', 'cc6ba2c0-7e0d-404d-a0e3-345ea178cb08', '2026-06-30', '2026-06-30')
ON CONFLICT (id) DO NOTHING;

INSERT INTO payroll_line_item (id, payroll_entry_id, idx, task_submission_id, rate, quantity, amount, created_by, created_at, updated_at)
VALUES ('PLI-00023', 'PE-00022', 1, 'SUB-00022', 40.00, 1, 40.00, 'cc6ba2c0-7e0d-404d-a0e3-345ea178cb08', '2026-06-30', '2026-06-30')
ON CONFLICT (id) DO NOTHING;

-- === Period 1 (July 1-15, DRAFT - current period) ===
-- Jane: 1 task (docs $50) = $50
INSERT INTO payroll_entry (id, payroll_period_id, user_id, total_tasks, total_amount, status, generated_at, created_by, created_at, updated_at)
VALUES ('PE-00011', 'PP-00001', 'wkr-0001-aaaa-bbbb-cccc-000000000001', 1, 50.00, 'draft', '2026-07-15 12:00:00', 'cc6ba2c0-7e0d-404d-a0e3-345ea178cb08', '2026-07-15', '2026-07-15')
ON CONFLICT (id) DO NOTHING;

INSERT INTO payroll_line_item (id, payroll_entry_id, idx, task_submission_id, rate, quantity, amount, created_by, created_at, updated_at)
VALUES ('PLI-00011', 'PE-00011', 1, 'SUB-00030', 50.00, 1, 50.00, 'cc6ba2c0-7e0d-404d-a0e3-345ea178cb08', '2026-07-15', '2026-07-15')
ON CONFLICT (id) DO NOTHING;

-- Carlos: 1 task (dev $75) = $75
INSERT INTO payroll_entry (id, payroll_period_id, user_id, total_tasks, total_amount, status, generated_at, created_by, created_at, updated_at)
VALUES ('PE-00012', 'PP-00001', 'wkr-0002-aaaa-bbbb-cccc-000000000002', 1, 75.00, 'draft', '2026-07-15 12:00:00', 'cc6ba2c0-7e0d-404d-a0e3-345ea178cb08', '2026-07-15', '2026-07-15')
ON CONFLICT (id) DO NOTHING;

INSERT INTO payroll_line_item (id, payroll_entry_id, idx, task_submission_id, rate, quantity, amount, created_by, created_at, updated_at)
VALUES ('PLI-00012', 'PE-00012', 1, 'SUB-00031', 75.00, 1, 75.00, 'cc6ba2c0-7e0d-404d-a0e3-345ea178cb08', '2026-07-15', '2026-07-15')
ON CONFLICT (id) DO NOTHING;

-- Aria: 1 task (design $60) = $60
INSERT INTO payroll_entry (id, payroll_period_id, user_id, total_tasks, total_amount, status, generated_at, created_by, created_at, updated_at)
VALUES ('PE-00013', 'PP-00001', 'wkr-0003-aaaa-bbbb-cccc-000000000003', 1, 60.00, 'draft', '2026-07-15 12:00:00', 'cc6ba2c0-7e0d-404d-a0e3-345ea178cb08', '2026-07-15', '2026-07-15')
ON CONFLICT (id) DO NOTHING;

INSERT INTO payroll_line_item (id, payroll_entry_id, idx, task_submission_id, rate, quantity, amount, created_by, created_at, updated_at)
VALUES ('PLI-00013', 'PE-00013', 1, 'SUB-00032', 60.00, 1, 60.00, 'cc6ba2c0-7e0d-404d-a0e3-345ea178cb08', '2026-07-15', '2026-07-15')
ON CONFLICT (id) DO NOTHING;

COMMIT;

-- ── Verification ─────────────────────────────────────────────────────
SELECT '=== PAYROLL SETTINGS ===' AS info;
SELECT id, currency, cutoff_rule, auto_approve_threshold, require_hr_approval FROM payroll_settings;

SELECT '=== PAYROLL PERIODS ===' AS info;
SELECT id, label, status, start_date, end_date FROM payroll_period ORDER BY start_date;

SELECT '=== PAYROLL ENTRIES ===' AS info;
SELECT pe.id, pe.payroll_period_id, pe.user_id, u.full_name, pe.total_tasks, pe.total_amount, pe.status
FROM payroll_entry pe
JOIN core_users u ON u.id = pe.user_id
ORDER BY pe.payroll_period_id, u.full_name;

SELECT '=== PAYROLL LINE ITEMS ===' AS info;
SELECT pli.id, pli.payroll_entry_id, pli.task_submission_id, pli.rate, pli.quantity, pli.amount
FROM payroll_line_item pli
ORDER BY pli.payroll_entry_id, pli.idx;
