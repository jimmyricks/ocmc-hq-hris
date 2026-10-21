export type PayrollPeriodStatus = 'open' | 'closed' | 'paid';
export type PayrollEntryStatus = 'draft' | 'under_review' | 'approved' | 'paid';

export interface PayrollPeriod {
	id: string;
	label: string;
	period_type?: string;
	start_date: string;
	end_date: string;
	cutoff?: string;
	status: PayrollPeriodStatus;
	is_auto_generated?: boolean;
	created_at?: string;
	updated_at?: string;
}

export interface PayrollEntry {
	id: string;
	payroll_period_id: string;
	user_id: string;
	total_tasks?: number;
	total_amount?: number;
	status: PayrollEntryStatus;
	generated_at?: string;
	approved_by?: string;
	approved_at?: string;
	created_at?: string;
	updated_at?: string;
}

export interface PayrollLineItem {
	id: string;
	payroll_entry_id: string;
	idx?: number;
	task_submission_id: string;
	rate?: number;
	quantity?: number;
	amount?: number;
	created_at?: string;
	updated_at?: string;
}

export interface PayrollSettings {
	id?: string;
	currency: string;
	cutoff_rule: string;
	auto_approve_threshold?: number;
	require_hr_approval: boolean;
	notify_users_on_payment: boolean;
	default_period_start_day: number;
	default_period_end_day: number;
	created_at?: string;
	updated_at?: string;
}

export interface UserTaskRate {
	id: string;
	workspace_id: string;
	task_type_id: string;
	user_id: string;
	rate: number;
	created_at?: string;
	updated_at?: string;
}

export interface EmployeeRateOptions {
	workspaces: Array<{ id: string; name: string }>;
	users: Array<{
		id: string;
		full_name: string;
		email: string;
		workspace_ids: string[];
	}>;
	task_types: Array<{
		id: string;
		workspace_id: string;
		name: string;
		unit_rate: number | null;
		unit: string | null;
	}>;
}
