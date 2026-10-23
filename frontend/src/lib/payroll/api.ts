import {
	apiJSON,
	listEntity,
	listFiltered,
	listFilteredPage,
	getEntityRecord,
	toPaginatedResult,
	type PaginatedResult,
} from '$lib/api/index.js';
import type { TaskType } from '$lib/task-manager/types.js';
import type {
	EmployeeRateOptions,
	PayrollEntry,
	PayrollInvoice,
	PayrollLineItem,
	PayrollPeriod,
	PayrollSettings,
	UserTaskRate
} from './types.js';

export const payrollApi = {
	async getEmployeeRates(): Promise<UserTaskRate[]> {
		const res = await apiJSON('/api/payroll/rates?page=1&page_size=200');
		return (res.data ?? []) as UserTaskRate[];
	},

	async getEmployeeRatesPage(
		page = 1,
		pageSize = 50,
		search = '',
	): Promise<PaginatedResult<UserTaskRate>> {
		const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
		if (search.trim()) params.set('search', search.trim());
		const res = await apiJSON(`/api/payroll/rates?${params}`);
		return toPaginatedResult<UserTaskRate>(res, page, pageSize);
	},

	async getTaskTypesPage(
		page = 1,
		pageSize = 50,
		search = '',
	): Promise<PaginatedResult<TaskType>> {
		const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
		if (search.trim()) params.set('search', search.trim());
		const res = await apiJSON(`/api/payroll/task-types?${params}`);
		return toPaginatedResult<TaskType>(res, page, pageSize);
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

	async getMyInvoicesPage(
		page = 1,
		pageSize = 25,
	): Promise<PaginatedResult<PayrollInvoice>> {
		const params = new URLSearchParams({
			page: String(page),
			page_size: String(pageSize),
		});
		const response = await apiJSON(`/api/payroll/my-invoices?${params}`);
		return toPaginatedResult<PayrollInvoice>(response, page, pageSize);
	},

	async getPeriods(): Promise<PayrollPeriod[]> {
		const firstPage = await this.getPeriodsPage(1, 100);
		const pages = await Promise.all(
			Array.from(
				{ length: Math.max(0, Math.ceil(firstPage.total / firstPage.page_size) - 1) },
				(_, index) => this.getPeriodsPage(index + 2, 100),
			),
		);
		return [...firstPage.items, ...pages.flatMap((page) => page.items)];
	},

	async getPeriodsPage(page = 1, pageSize = 50): Promise<PaginatedResult<PayrollPeriod>> {
		const res = await listFilteredPage<PayrollPeriod>('payroll_period', [], page, pageSize, {
			sortField: 'start_date',
			sortOrder: 'desc',
		});
		return res;
	},

	async getPeriod(periodId: string): Promise<PayrollPeriod> {
		const res = await apiJSON(`/api/payroll/periods/${encodeURIComponent(periodId)}`);
		return res.data as PayrollPeriod;
	},

	async getEntriesForPeriod(periodId: string): Promise<PayrollEntry[]> {
		const firstPage = await this.getEntriesForPeriodPage(periodId, 1, 100);
		const pages = await Promise.all(
			Array.from(
				{ length: Math.max(0, Math.ceil(firstPage.total / firstPage.page_size) - 1) },
				(_, index) => this.getEntriesForPeriodPage(periodId, index + 2, 100),
			),
		);
		return [...firstPage.items, ...pages.flatMap((page) => page.items)];
	},

	async getEntriesForPeriodPage(
		periodId: string,
		page = 1,
		pageSize = 50,
	): Promise<PaginatedResult<PayrollEntry>> {
		const params = new URLSearchParams({
			page: String(page),
			page_size: String(pageSize),
		});
		const response = await apiJSON(
			`/api/payroll/periods/${encodeURIComponent(periodId)}/entries?${params}`,
		);
		return toPaginatedResult<PayrollEntry>(response, page, pageSize);
	},

	async getEntryForPeriod(periodId: string, entryId: string): Promise<PayrollEntry> {
		const response = await apiJSON(
			`/api/payroll/periods/${encodeURIComponent(periodId)}/entries/${encodeURIComponent(entryId)}`,
		);
		return response.data as PayrollEntry;
	},

	async getLineItemsForEntry(entryId: string): Promise<PayrollLineItem[]> {
		const res = await listFiltered('payroll_line_item', [
			{ field: 'payroll_entry_id', op: 'eq', value: entryId },
		], 1, 100);
		return (res.data ?? []) as PayrollLineItem[];
	},

	async getLineItemsForEntryPage(
		entryId: string,
		page = 1,
		pageSize = 25,
	): Promise<PaginatedResult<PayrollLineItem>> {
		return listFilteredPage<PayrollLineItem>(
			'payroll_line_item',
			[{ field: 'payroll_entry_id', op: 'eq', value: entryId }],
			page,
			pageSize,
			{ sortField: 'idx', sortOrder: 'asc' },
		);
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
	async getLineItemTaskInfo(submissionId: string): Promise<{ taskTitle: string; taskTypeName?: string; submissionNotes?: string }> {
		const unavailable = { taskTitle: 'Task details unavailable' };
		try {
			const subResponse = await getEntityRecord('task_submission', submissionId);
			const sub = subResponse.data;
			const assignmentId = (sub as any)?.task_assignment_id;
			if (!assignmentId) return unavailable;
			const assignmentResponse = await getEntityRecord('task_assignment', assignmentId);
			const assignment = assignmentResponse.data;
			const taskId = (assignment as any)?.task_id;
			if (!taskId) return unavailable;
			const taskResponse = await getEntityRecord('task', taskId);
			const task = taskResponse.data;
			const taskTypeName = (task as any)?.task_type_id
				? (await getEntityRecord('task_type', (task as any).task_type_id)).data?.name
				: undefined;
			return {
				taskTitle: (task as any)?.title ?? unavailable.taskTitle,
				taskTypeName,
				submissionNotes: (sub as any)?.notes,
			};
		} catch {
			return unavailable;
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
