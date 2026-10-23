export interface WorkflowCatalogState {
  id: string;
  label: string;
  slug: string;
  color?: string;
}

export interface WorkflowCatalogAction {
  id: string;
  label: string;
  slug: string;
}

export interface WorkflowSummary {
  id: string;
  name: string;
  target_entity: string;
  workspace_id?: string | null;
  workspace_name?: string;
  is_active: boolean;
  is_default: boolean;
  states_count: number;
  transitions_count: number;
}

export interface WorkflowStateLink {
  id: string;
  state_id: string;
  state_slug: string;
  state_label: string;
  state_color?: string;
  is_initial: boolean;
  sort_order?: number;
  visual_config?: Record<string, unknown>;
}

export interface WorkflowTransitionRecord {
  id: string;
  from_state_link_id: string;
  from_state_slug: string;
  action_id: string;
  action_slug: string;
  action_label: string;
  to_state_link_id: string;
  to_state_slug: string;
  sort_order?: number;
  allowed_roles: string[];
  visual_config?: Record<string, unknown>;
}

export interface WorkflowDetail {
  id: string;
  name: string;
  target_entity: string;
  workspace_id?: string | null;
  is_active: boolean;
  is_default: boolean;
  state_links: WorkflowStateLink[];
  transitions: WorkflowTransitionRecord[];
}

export interface WorkflowSavePayload {
  name: string;
  target_entity?: string;
  workspace_id?: string | null;
  is_active: boolean;
  is_default: boolean;
  state_links?: Array<{
    state_id: string;
    is_initial: boolean;
    sort_order: number;
    visual_config?: Record<string, unknown>;
  }>;
  transitions?: Array<{
    from_state_id: string;
    action_id: string;
    to_state_id: string;
    allowed_roles: string[];
    visual_config?: Record<string, unknown>;
  }>;
}
