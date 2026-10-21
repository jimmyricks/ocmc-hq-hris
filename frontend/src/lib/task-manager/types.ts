export type ProjectStatus = 'active' | 'archived' | 'closed';
export type TaskStatus = 'pending' | 'in_progress' | 'for_review' | 'submitted' | 'needs_revision' | 'approved' | 'closed' | 'cancelled';
export type Priority = 'low' | 'medium' | 'high' | 'urgent';

// workflow_state IS the task status (single field). See user-journey.md Journey 7.
export type WorkflowState =
	| 'draft_assigned'
	| 'in_progress'
	| 'for_review'
	| 'needs_revision'
	| 'approved'
	| 'closed';

export type ApprovalDecision = 'approved' | 'rejected' | 'needs_revision';

export interface WorkflowTransition {
	action: string;
	label: string;
	from_state: string;
	to_state: string;
}

export interface WorkflowProgress {
	entity: string;
	record_id: string;
	current_state: string | null;
	available_transitions: WorkflowTransition[];
}

export interface ProjectMember {
	id: string;
	project_id: string;
	user_id: string;
	role?: string;
	created_at?: string;
	updated_at?: string;
}

export interface Project {
	id: string;
	name: string;
	workspace_id?: string;
	team_id?: string | null;
	description?: string;
	color?: string;
	icon?: string;
	manager_id: string;
	status?: ProjectStatus;
	start_date?: string;
	end_date?: string;
	is_continuous?: boolean;
	created_at?: string;
	updated_at?: string;
}

export interface User {
	id: string;
	username?: string;
	email: string;
	full_name: string;
	first_name?: string;
	last_name?: string;
	contact_number?: string;
	department?: string;
	site?: string;
	employee_id?: string;
	is_active: boolean;
	is_superuser?: boolean;
	created_at?: string;
	updated_at?: string;
}

export interface TaskType {
	id: string;
	name: string;
	description?: string;
	unit_rate: number;
	unit: string;
	requires_approval?: boolean;
	created_at?: string;
	updated_at?: string;
}

export interface TaskCategory {
	id: string;
	name: string;
	color?: string;
	icon?: string;
	created_at?: string;
	updated_at?: string;
}

export interface Task {
	id: string;
	project_id: string;
	task_type_id: string;
	category_id?: string;
	title: string;
	description?: string;
	priority: Priority;
	status: TaskStatus;
	workflow_state?: WorkflowState;
	task_key?: string;
	created_by?: string;
	due_date?: string;
	links?: TaskLink[];
	created_at?: string;
	updated_at?: string;
}

export interface TaskAssignment {
	id: string;
	task_id: string;
	idx?: number;
	user_id: string;
	assigned_by?: string;
	assigned_at?: string;
	unassigned_at?: string;
	is_active?: boolean;
	status?: string;
	created_at?: string;
	updated_at?: string;
}

export interface TaskLink {
	id: string;
	task_id: string;
	url: string;
	label?: string;
	created_at?: string;
	updated_at?: string;
}

export type SubmissionStatus = 'draft' | 'submitted' | 'under_review' | 'needs_revision' | 'approved' | 'rejected';

export interface TaskSubmission {
	id: string;
	task_assignment_id: string;
	version?: number;
	previous_submission_id?: string;
	notes?: string;
	status: SubmissionStatus;
	submitted_by?: string;
	submitted_at?: string;
	external_link?: string;
	created_at?: string;
	updated_at?: string;
}

export interface TaskApproval {
	id: string;
	task_submission_id: string;
	idx?: number;
	approver_id?: string;
	decision: ApprovalDecision;
	remarks?: string;
	decided_at?: string;
	created_at?: string;
	updated_at?: string;
}

export interface Comment {
	id: string;
	entity_name: string;
	record_id: string;
	parent_id?: string | null;
	body: string;
	author_id: string;
	author_username?: string;
	is_edited?: boolean;
	created_at?: string;
	updated_at?: string;
}
