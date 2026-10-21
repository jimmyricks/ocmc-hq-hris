import { apiJSON, listEntity, listFiltered, getEntityRecord } from '$lib/api/index.js';
import type {
	EmployeeRateOptions,
	PayrollEntry,
	PayrollLineItem,
	PayrollPeriod,
	PayrollSettings,
	UserTaskRate
} from './types.js';

export const payrollApi = {
	async getEmployeeRates(): Promise<UserTaskRate[]> {
		const res = await apiJSON('/api/payroll/rates');
		return (res.data ?? []) as UserTaskRate[];
	},

	async getEmployeeRateOptions(workspaceId?: string): Promise<EmployeeRateOptions> {
		const query = workspaceId
			? `?workspace_id=${encodeURIComponent(workspaceId)}`
			: '';
		const res = await apiJSON(`/api/payroll/rate-options${query}`);
		return res.data as EmployeeRateOptions;
	},

	async saveEmployeeRate(
		payload: Omit<UserTaskRate, 'id' | 'created_at' | 'updated_at'>,
		id?: string
	): Promise<UserTaskRate> {
		const res = await apiJSON(id ? `/api/payroll/rates/${id}` : '/api/payroll/rates', {
			method: id ? 'PUT' : 'POST',
			body: JSON.stringify(payload)
		});
		return res.data as UserTaskRate;
	},

	async deleteEmployeeRate(id: string): Promise<void> {
		await apiJSON(`/api/payroll/rates/${id}`, { method: 'DELETE' });
	},

	async getHrSummary(): Promise<{
		period_count: number;
		entry_count: number;
		approved_submission_count: number;
		payroll_total: number;
		invoice_total: number;
	}> {
		const res = await apiJSON('/api/payroll/hr/summary');
		return res.data;
	},

	async getPeriods(): Promise<PayrollPeriod[]> {
		const res = await listEntity('payroll_period', 1, 100);
		return (res.data ?? []) as PayrollPeriod[];
	},

	async getEntriesForPeriod(periodId: string): Promise<PayrollEntry[]> {
		const res = await listFiltered('payroll_entry', [
			{ field: 'payroll_period_id', op: 'eq', value: periodId },
		], 1, 100);
		return (res.data ?? []) as PayrollEntry[];
	},

	async getLineItemsForEntry(entryId: string): Promise<PayrollLineItem[]> {
		const res = await listFiltered('payroll_line_item', [
			{ field: 'payroll_entry_id', op: 'eq', value: entryId },
		], 1, 100);
		return (res.data ?? []) as PayrollLineItem[];
	},

	async getSettings(): Promise<PayrollSettings | null> {
		const res = await listEntity('payroll_settings', 1, 10);
		return (res.data?.[0] as PayrollSettings) ?? null;
	},

	async saveSettings(data: Partial<PayrollSettings>, id?: string): Promise<PayrollSettings> {
		const body = JSON.stringify({ data });
		const res = id
			? await apiJSON(`/api/entity/payroll_settings/${id}`, { method: 'PUT', body })
			: await apiJSON('/api/entity/payroll_settings', { method: 'POST', body });
		return res.data as PayrollSettings;
	},

	/**
	 * Fetch task submission + its parent task for a line item,
	 * so the breakdown can show the task title alongside the rate.
	 */
	async getLineItemTaskInfo(submissionId: string): Promise<{ taskTitle: string; taskKey?: string; taskTypeName?: string; submissionNotes?: string }> {
		try {
			const sub = await getEntityRecord('task_submission', submissionId);
			const assignmentId = (sub as any)?.task_assignment_id;
			if (!assignmentId) return { taskTitle: submissionId };
			const assignment = await getEntityRecord('task_assignment', assignmentId);
			const taskId = (assignment as any)?.task_id;
			if (!taskId) return { taskTitle: submissionId };
			const task = await getEntityRecord('task', taskId);
			const taskTypeName = (task as any)?.task_type_id
				? ((await getEntityRecord('task_type', (task as any).task_type_id)) as any)?.name
				: undefined;
			return {
				taskTitle: (task as any)?.title ?? submissionId,
				taskKey: (task as any)?.id,
				taskTypeName,
				submissionNotes: (sub as any)?.notes,
			};
		} catch {
			return { taskTitle: submissionId };
		}
	},

	async createPeriod(payload: {
		label?: string;
		period_type?: string;
		start_date: string;
		end_date: string;
		cutoff?: string;
	}): Promise<PayrollPeriod> {
		const res = await apiJSON('/api/payroll/periods', {
			method: 'POST',
			body: JSON.stringify(payload),
		});
		return res.data as PayrollPeriod;
	},

	async generate(periodId: string): Promise<{ count: number; entries: PayrollEntry[] }> {
		const res = await apiJSON('/api/payroll/periods/generate', {
			method: 'POST',
			body: JSON.stringify({ payroll_period_id: periodId }),
		});
		return res.data as { count: number; entries: PayrollEntry[] };
	},

	async approveEntry(entryId: string): Promise<PayrollEntry> {
		const res = await apiJSON(`/api/payroll/entries/${entryId}/approve`, { method: 'POST' });
		return res.data as PayrollEntry;
	},

	async payEntry(entryId: string): Promise<PayrollEntry> {
		const res = await apiJSON(`/api/payroll/entries/${entryId}/pay`, { method: 'POST' });
		return res.data as PayrollEntry;
	},
};
