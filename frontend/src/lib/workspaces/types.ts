export interface Workspace {
  id: string;
  name: string;
  slug: string;
  color: string;
  timezone: string;
  is_active: boolean;
  membership_role?: "member" | "supervisor" | null;
  is_home?: boolean;
  can_manage?: boolean;
}

export interface WorkspaceContext {
  active_workspace_id: string | null;
  home_workspace_id: string | null;
  is_global: boolean;
  can_manage: boolean;
  capabilities?: {
    can_manage_active_workspace: boolean;
    can_manage_payroll: boolean;
    can_view_global_schedule: boolean;
    can_view_hr_directory: boolean;
    is_system_admin: boolean;
    can_view_all_workspaces?: boolean;
  };
  workspaces: Workspace[];
}

export interface PlannerActivity {
  id: string;
  source_type:
    | "task"
    | "planner_event"
    | "schedule_occurrence"
    | "project_start"
    | "project_deadline"
    | "schedule_summary";
  source_id: string;
  kind: string;
  title: string;
  starts_at: string | null;
  ends_at: string | null;
  all_day: boolean;
  status: string;
  workspace: {
    id: string;
    name: string;
    color: string;
  };
  project: {
    id: string;
    name: string;
  } | null;
  resources: Array<{
    id: string;
    name: string;
    resource_type: string;
    status: string;
  }>;
  team: {
    id: string;
    name: string;
  } | null;
  summary_only?: boolean;
  resource_label?: string | null;
}

export interface PlannerScheduleSummary {
  kind: string;
  starts_at: string | null;
  ends_at: string | null;
  all_day: boolean;
  status: string;
  workspace: {
    id: string;
    name: string;
    color: string;
  };
  resource_label: string | null;
}

export interface DirectoryUser {
  id: string;
  username: string;
  email: string;
  full_name: string;
  is_active: boolean;
}
