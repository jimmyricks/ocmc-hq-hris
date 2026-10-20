import { apiJSON } from '$lib/api/index.js';
import type { AuditLog, Ledger } from './types.js';

export type AuditLogFilters = {
	reference_entity?: string;
	reference_id?: string;
	action?: string;
	actor_id?: string;
	date_from?: string;
	date_to?: string;
};

export type LedgerFilters = {
	user_id?: string;
	entry_type?: string;
	reference_entity?: string;
	period_from?: string;
	period_to?: string;
};

function buildQuery(filters: Record<string, string | undefined>): string {
	const params = new URLSearchParams();
	for (const [key, value] of Object.entries(filters)) {
		if (value?.trim()) {
			params.set(key, value.trim());
		}
	}
	const query = params.toString();
	return query ? `?${query}` : '';
}

export interface PaginatedResult<T> {
	total: number;
	page: number;
	page_size: number;
	items: T[];
}

export const auditApi = {
	async getAuditLogs(
		filters: AuditLogFilters = {},
		page = 1,
		page_size = 50,
	): Promise<PaginatedResult<AuditLog>> {
		const query = buildQuery({ ...filters, page: String(page), page_size: String(page_size) });
		const res = await apiJSON(`/api/audit-ledger/audit-logs${query}`);
		return res.data as PaginatedResult<AuditLog>;
	},

	async getLedger(
		filters: LedgerFilters = {},
		page = 1,
		page_size = 50,
	): Promise<PaginatedResult<Ledger>> {
		const query = buildQuery({ ...filters, page: String(page), page_size: String(page_size) });
		const res = await apiJSON(`/api/audit-ledger/ledger${query}`);
		return res.data as PaginatedResult<Ledger>;
	},
};
