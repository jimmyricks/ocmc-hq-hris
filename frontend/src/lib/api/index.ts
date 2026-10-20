import { getToken, getRefreshToken, setToken, clearAuth } from '$lib/auth';
import { browser } from '$app/environment';
import { getActiveWorkspaceId } from '$lib/workspaces/context';

const API_BASE = ''; // use relative paths; Vite proxy forwards /api and /uploads to the backend

// ---------------------------------------------------------------------------
// Token refresh single-flight
// ---------------------------------------------------------------------------
// When the access token expires, many parallel requests may fail with 401 at
// once. We only want ONE /api/auth/refresh call in flight; every other caller
// awaits the same promise and retries with the freshly issued access token.

let refreshPromise: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
	if (refreshPromise) return refreshPromise;

	refreshPromise = (async () => {
		const refreshToken = getRefreshToken();
		// The backend also reads the refresh token from an httponly cookie, so
		// sending the body is a fallback for cross-origin / non-cookie setups.
		const body: Record<string, string> = {};
		if (refreshToken) body.refresh_token = refreshToken;

		try {
			const res = await fetch(`${API_BASE}/api/auth/refresh`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(body),
				credentials: 'include'
			});
			if (!res.ok) return null;
			const json = (await res.json()) as { access_token?: string };
			const newToken = json.access_token ?? null;
			if (newToken) setToken(newToken);
			return newToken;
		} catch {
			return null;
		} finally {
			refreshPromise = null;
		}
	})();

	return refreshPromise;
}

function redirectToLogin() {
	if (browser && !location.pathname.startsWith('/login')) {
		location.assign('/login');
	}
}

export class ApiError extends Error {
	status: number;
	details?: Record<string, any>;
	constructor(message: string, status: number, details?: Record<string, any>) {
		super(message);
		this.name = 'ApiError';
		this.status = status;
		this.details = details;
	}
}

export interface ApiRequestOptions extends RequestInit {
	timeout?: number;
	skipAuth?: boolean;
	skipContentType?: boolean;
}

function formatDetails(json: Record<string, any>): string {
	const details = json.details || json.errors;
	if (!details) return '';
	if (Array.isArray(details)) {
		return details.map((e: any) => {
			if (typeof e === 'string') return e;
			if (e.field && e.message) return `${e.field}: ${e.message}`;
			return String(e);
		}).join('; ');
	}
	if (details.errors && Array.isArray(details.errors)) {
		return details.errors.map((e: any) => `${e.field}: ${e.message}`).join('; ');
	}
	if (typeof details === 'object') {
		return Object.entries(details)
			.map(([k, v]) => `${k}: ${v}`)
			.join('; ');
	}
	return String(details);
}

function extractMessage(json: Record<string, any>, status: number): string {
	const base = (json.message as string) || (json.detail as string) || '';
	const details = formatDetails(json);
	if (base && details) return `${base} (${details})`;
	if (base) return base;
	if (details) return details;
	return `Request failed with status ${status}`;
}

export async function apiFetch(path: string, options: ApiRequestOptions = {}): Promise<Response> {
	const {
		timeout = 30000,
		skipAuth = false,
		skipContentType = false,
		...fetchOptions
	} = options;

	async function doFetch(): Promise<Response> {
		const token = getToken();
		const headers = new Headers(fetchOptions.headers);

		// Add authentication header
		if (!skipAuth && token) {
			headers.set('Authorization', `Bearer ${token}`);
		}
		const workspaceId = getActiveWorkspaceId();
		if (workspaceId) headers.set('X-Workspace-ID', workspaceId);

		// Add Content-Type for JSON bodies
		if (
			!skipContentType &&
			fetchOptions.body &&
			!(fetchOptions.body instanceof FormData || fetchOptions.body instanceof URLSearchParams)
		) {
			headers.set('Content-Type', 'application/json');
		}

		// Create abort controller for timeout
		const controller = new AbortController();
		const timeoutId = setTimeout(() => controller.abort(), timeout);

		try {
			const res = await fetch(`${API_BASE}${path}`, {
				...fetchOptions,
				headers,
				signal: controller.signal,
				credentials: 'include'
			});

			clearTimeout(timeoutId);
			return res;
		} catch (error) {
			clearTimeout(timeoutId);

			if (error instanceof Error && error.name === 'AbortError') {
				throw new ApiError('Request timeout', 408);
			}

			throw error;
		}
	}

	const res = await doFetch();

	// 401 → try to refresh the access token once, then retry the original
	// request. Only attempt refresh for authenticated requests (skipAuth=false)
	// and never recurse into the refresh endpoint itself.
	if (res.status === 401 && browser && !skipAuth && !path.startsWith('/api/auth/refresh')) {
		const newToken = await refreshAccessToken();
		if (newToken) {
			return doFetch();
		}
		// Refresh failed — session is truly dead.
		clearAuth();
		redirectToLogin();
	}

	return res;
}

export async function apiJSON(path: string, options: RequestInit = {}) {
	const res = await apiFetch(path, options);
	const text = await res.text();
	let json: Record<string, any> = {};
	if (text) {
		try {
			json = JSON.parse(text) as Record<string, any>;
		} catch {
			json = { status: 'error', message: text };
		}
	}

	// Backend may return 200 with status: 'error' (ActionResponse) or a non-2xx with message/detail.
	if (!res.ok || json.status === 'error') {
		const message = extractMessage(json, res.status);
		throw new ApiError(message, res.status, json.details || json.errors);
	}
	return json;
}

export async function login(username: string, password: string) {
	const body = new URLSearchParams({ username, password });
	return apiJSON('/api/auth/login', { method: 'POST', body });
}

export type EntityFilter = {
	field: string;
	op: string;
	value: any;
};

export async function listEntity(entity: string, page = 1, pageSize = 20) {
	const normalized = normalizeEntity(entity);
	return apiJSON(`/api/entity/${normalized}/list?page=${page}&page_size=${pageSize}`);
}

export async function listFiltered(entity: string, filters: EntityFilter[], page = 1, pageSize = 100) {
	const normalized = normalizeEntity(entity);
	const filtersParam = encodeURIComponent(JSON.stringify(filters));
	return apiJSON(`/api/entity/${normalized}/list?filters=${filtersParam}&page=${page}&page_size=${pageSize}`);
}

export async function getEntityRecord(entity: string, id: string) {
	const normalized = normalizeEntity(entity);
	return apiJSON(`/api/entity/${normalized}/detail/${id}`);
}

export async function saveEntity(entity: string, data: Record<string, any>, id?: string) {
	const normalized = normalizeEntity(entity);
	const body = JSON.stringify({ data });
	if (id) {
		// Update existing record via PUT (RESTful)
		return apiJSON(`/api/entity/${normalized}/${id}`, { method: 'PUT', body });
	}
	// Create new record via POST (RESTful) -> 201 Created
	return apiJSON(`/api/entity/${normalized}`, { method: 'POST', body });
}

export async function deleteEntity(entity: string, id: string) {
	const normalized = normalizeEntity(entity);
	return apiJSON(`/api/entity/${normalized}/${id}`, { method: 'DELETE' });
}

function normalizeEntity(entity: string): string {
	const mappings: Record<string, string> = {
		tasks: "task",
		users: "user",
		projects: "project",
		"task-types": "task_type",
		"payroll-periods": "payroll_period",
		"payroll-entries": "payroll_entry",
		"payroll-line-items": "payroll_line_item",
		"task-assignments": "task_assignment",
		"task-submissions": "task_submission",
		"task-approvals": "task_approval",
		departments: "department",
		comments: "oc_comment",
		ledgers: "ledger",
		notifications: "notification",
		"audit-logs": "oc_audit_log"
	};
	return mappings[entity] || entity.replace(/-/g, "_");
}
