// Auto-generated TypeScript types from entity metadata
// Do not edit manually - run: python -m app.forge generate-types

export interface BaseEntity {
  id: string
  created_at: string
  updated_at: string
}

export interface Attachment extends BaseEntity {
  entity_name: string
  record_id: string
  file_name: string
  original_name: string
  file_path: string
  file_size: number
  mime_type?: string
  uploaded_by?: string
  description?: string
}

export interface AuditLog extends BaseEntity {
  entity_name: string
  record_id: string
  action: string
  user_id?: string
  username?: string
  before_snapshot?: string
  after_snapshot?: string
  changed_fields?: string
}

export interface Department extends BaseEntity {
  name: string
  head_user_id?: string
}

export interface EmailLog extends BaseEntity {
  subject?: string
  recipients?: string
  cc?: string
  bcc?: string
  from_address?: string
  entity_name?: string
  record_id?: string
  event_type?: string
  status?: string
  error_message?: string
  html_body?: string
  sent_at?: string
  sent_by?: string
}

export interface EntityOrder extends BaseEntity {
  entity_name: string
  module_name: string
  sort_order: number
}

export interface EntityPermission extends BaseEntity {
  role: string
  entity_name: string
  can_read: boolean
  can_create: boolean
  can_update: boolean
  can_delete: boolean
  can_select: boolean
  can_export: boolean
  can_import: boolean
  in_sidebar: boolean
  row_scope: string
}

export interface ErrorLog extends BaseEntity {
  status?: number
  title?: string
  message?: string
}

export interface Ledger extends BaseEntity {
  reference_entity: string
  reference_id: string
  user_id: string
  amount: number
  entry_type: string
  description?: string
  period: string
}

export interface ModuleOrder extends BaseEntity {
  module_name: string
  sort_order: number
}

export interface Notification extends BaseEntity {
  user_id: string
  reference_entity?: string
  reference_id?: string
  type: string
  message: string
  is_read: boolean
}

export interface NotificationSubscription extends BaseEntity {
  user_id?: string
  entity_type?: string
  entity_id?: string
  event?: string
  recipient_email?: string
  is_active?: boolean
}

export interface OcAuditLog extends BaseEntity {
  reference_entity: string
  reference_id: string
  action: string
  old_values?: string
  new_values?: string
  actor_id: string
  ip_address?: string
  timestamp: string
}

export interface OcComment extends BaseEntity {
  reference_entity: string
  reference_id: string
  comment_by: string
  comment_text: string
}

export interface PayrollEntry extends BaseEntity {
  payroll_period_id: string
  user_id: string
  total_tasks: number
  total_amount: number
  status: string
  generated_at: string
  approved_by?: string
  approved_at?: string
}

export interface PayrollLineItem extends BaseEntity {
  payroll_entry_id: string
  idx: number
  task_submission_id: string
  rate: number
  quantity: number
  amount: number
}

export interface PayrollPeriod extends BaseEntity {
  label: string
  period_type: string
  start_date: string
  end_date: string
  cutoff: string
  status: string
  is_auto_generated: boolean
}

export interface Project extends BaseEntity {
  name: string
  description?: string
  color?: string
  icon?: string
  manager_id: string
  status?: string
  start_date?: string
  end_date?: string
}

export interface QrCode extends BaseEntity {
  source_type: string
  source_value: string
  short_link_id?: string
  error_correction_level: string
  size: number
  format: string
  fg_color: string
  bg_color: string
}

export interface Role extends BaseEntity {
  name: string
  description?: string
  is_active: boolean
}

export interface ScheduledJobLog extends BaseEntity {
  job_id: string
  job_name: string
  status: string
  started_at: string
  completed_at?: string
  duration_seconds?: number
  records_created?: number
  records_updated?: number
  error_message?: string
  error_traceback?: string
  details?: string
  trigger_type?: string
  cron_expression?: string
}

export interface ShortLink extends BaseEntity {
  slug: string
  destination_url: string
  title?: string
  is_active?: boolean
  expires_at?: string
  password_hash?: string
  show_preview?: boolean
  click_count?: number
}

export interface ShortLinkClick extends BaseEntity {
  short_link_id: string
  clicked_at: string
  ip_hash?: string
  user_agent?: string
  referer?: string
  country?: string
}

export interface Task extends BaseEntity {
  project_id: string
  task_type_id: string
  category_id?: string
  title: string
  description?: string
  priority: string
  status: string
  due_date?: string
}

export interface TaskApproval extends BaseEntity {
  task_submission_id: string
  idx: number
  approver_id: string
  decision: string
  remarks?: string
  decided_at: string
}

export interface TaskAssignment extends BaseEntity {
  task_id: string
  idx?: number
  user_id: string
  assigned_by?: string
  assigned_at?: string
  unassigned_at?: string
  is_active?: boolean
  status?: string
}

export interface TaskCategory extends BaseEntity {
  name: string
  color?: string
  icon?: string
}

export interface TaskLink extends BaseEntity {
  task_id: string
  url: string
  label?: string
}

export interface TaskSubmission extends BaseEntity {
  task_assignment_id: string
  version: number
  previous_submission_id?: string
  notes?: string
  status: string
  submitted_by: string
  submitted_at: string
  external_link?: string
}

export interface TaskType extends BaseEntity {
  name: string
  description?: string
  unit_rate: number
  unit: string
  requires_approval?: boolean
}

export interface User extends BaseEntity {
  username?: string
  email: string
  full_name: string
  first_name?: string
  last_name?: string
  contact_number?: string
  department?: string
  site?: string
  employee_id?: string
  is_active: boolean
  is_superuser?: boolean
}

export interface UserActivity extends BaseEntity {
  user_id: string
  username: string
  activity_type: string
  entity_name?: string
  page_path?: string
  page_label?: string
  visit_count: number
  score: number
  last_visited_at: string
}

export interface Users extends BaseEntity {
  full_name: string
  email: string
  role: string
  department?: string
  status: string
  phone?: string
  is_active: boolean
}

export interface Workflow extends BaseEntity {
  name: string
  target_entity: string
  is_active: boolean
}

export interface WorkflowAction extends BaseEntity {
  label: string
  slug?: string
}

export interface WorkflowLedger extends BaseEntity {
  entity_type: string
  record_id: string
  previous_state?: string
  next_state: string
  action?: string
  changed_by?: string
  changed_at?: string
  triggered_by_entity_type?: string
  triggered_by_record_id?: string
  notes?: string
}

export interface WorkflowState extends BaseEntity {
  label: string
  slug?: string
  color?: string
}

export interface WorkflowStateLink extends BaseEntity {
  workflow_id: string
  state_id: string
  is_initial: boolean
  sort_order: number
}

export interface WorkflowTransition extends BaseEntity {
  workflow_id: string
  from_state_id: string
  action_id: string
  to_state_id: string
  allowed_roles?: string
  sort_order: number
}
