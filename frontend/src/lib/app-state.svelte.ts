import { browser } from '$app/environment';
import { getContext, setContext } from 'svelte';
import { apiJSON } from '$lib/api/index.js';
import { clearAuth, getToken, getUser, setAuth, setUser, type User } from '$lib/auth';
import { refCache } from '$lib/task-manager/ref-cache.js';
import { setActiveWorkspaceId } from '$lib/workspaces/context';
import { workspaceApi } from '$lib/workspaces/api';
import type { WorkspaceContext } from '$lib/workspaces/types';

const APP_STATE_CONTEXT = Symbol('app-state');
const TABLE_PAGE_TTL_MS = 3 * 60 * 1000;

export interface EntityPermissionSet {
	can_read?: boolean;
	can_create?: boolean;
	can_update?: boolean;
	can_delete?: boolean;
	can_select?: boolean;
	can_export?: boolean;
	can_import?: boolean;
	in_sidebar?: boolean;
	row_scope?: string | string[];
}

export interface BootPayload {
	user: User;
	permissions: Record<string, EntityPermissionSet>;
	sidebar?: {
		entities?: Array<Record<string, unknown>>;
		navigation?: Array<Record<string, unknown>>;
	};
	allowed_dashboards?: Array<Record<string, unknown>>;
	workflow_states?: Array<{ id: string; label: string; slug: string; color?: string }>;
	branding_settings?: Record<string, unknown>;
	workspace_context: WorkspaceContext | null;
	feature_flags?: Record<string, boolean>;
}

export interface LoginBootPayload extends BootPayload {
	access_token: string;
	refresh_token?: string;
	token_type: string;
}

type TablePageEntry = {
	page: number;
	expiresAt: number;
};

function assertBootPayload(payload: BootPayload): void {
	if (
		!payload?.user ||
		!payload?.permissions ||
		typeof payload.permissions !== 'object' ||
		Array.isArray(payload.permissions)
	) {
		throw new Error('Could not load your workspace permissions. Please try again.');
	}
}

export class AppState {
	user = $state<User | null>(browser ? getUser() : null);
	boot = $state<BootPayload | null>(null);
	bootLoading = $state(false);
	bootError = $state('');
	bootReady = $derived(
		this.boot !== null &&
			this.boot.user !== null &&
			typeof this.boot.permissions === 'object' &&
			this.boot.permissions !== null &&
			!Array.isArray(this.boot.permissions),
	);
	workspaceContext = $derived(this.boot?.workspace_context ?? null);
	capabilities = $derived(this.workspaceContext?.capabilities ?? null);
	isSystemAdmin = $derived(
		Boolean(
			this.capabilities?.is_system_admin ??
				this.user?.is_superuser ??
				this.user?.roles?.some((role) =>
					['Administrator', 'SystemManager'].includes(role),
				),
		),
	);
	permissions = $derived(this.boot?.permissions ?? {});
	private tablePages = $state<Record<string, TablePageEntry>>({});
	private bootPromise: Promise<BootPayload | null> | null = null;

	async signIn(username: string, password: string): Promise<BootPayload> {
		const body = new URLSearchParams({ username, password });
		const response = (await apiJSON('/api/auth/boot', {
			method: 'POST',
			body,
		})) as LoginBootPayload;
		assertBootPayload(response);
		setAuth(response.access_token, response.user, response.refresh_token);
		this.applyBoot(response);
		return response;
	}

	async ensureBoot(): Promise<BootPayload | null> {
		if (!browser) return null;
		if (this.boot) return this.boot;
		if (!getToken()) {
			this.boot = null;
			this.user = null;
			return null;
		}
		if (this.bootPromise) return this.bootPromise;

		this.bootLoading = true;
		this.bootError = '';
		this.bootPromise = (async () => {
			try {
				const response = (await apiJSON('/api/auth/boot')) as BootPayload;
				this.applyBoot(response);
				return response;
			} catch (error) {
				this.bootError =
					error instanceof Error ? error.message : 'Could not load workspace access';
				return null;
			} finally {
				this.bootLoading = false;
				this.bootPromise = null;
			}
		})();
		return this.bootPromise;
	}

	async refreshBoot(): Promise<BootPayload | null> {
		this.boot = null;
		return this.ensureBoot();
	}

	applyBoot(payload: BootPayload): void {
		assertBootPayload(payload);
		refCache.invalidate();
		this.boot = payload;
		this.bootLoading = false;
		this.user = payload.user;
		this.bootError = '';
		setUser(payload.user);
		setActiveWorkspaceId(payload.workspace_context?.active_workspace_id ?? null);
	}

	async selectWorkspace(workspaceId: string | null): Promise<void> {
		await workspaceApi.select(workspaceId);
		setActiveWorkspaceId(workspaceId);
		this.clearTablePages();
		await this.refreshBoot();
	}

	signOut(): void {
		this.boot = null;
		this.bootLoading = false;
		this.bootPromise = null;
		this.user = null;
		this.bootError = '';
		this.tablePages = {};
		refCache.invalidate();
		clearAuth();
	}

	can(entity: string, permission: keyof EntityPermissionSet = 'can_read'): boolean {
		if (this.user?.is_superuser) return true;
		return Boolean(this.permissions[entity]?.[permission]);
	}

	canWorkspace(capability: keyof NonNullable<WorkspaceContext['capabilities']>): boolean {
		return Boolean(this.capabilities?.[capability]);
	}

	tablePage(tableId: string, scope = ''): number {
		const key = this.tablePageKey(tableId, scope);
		const entry = this.tablePages[key];
		if (!entry) return 1;
		if (entry.expiresAt <= Date.now()) {
			delete this.tablePages[key];
			return 1;
		}
		return entry.page;
	}

	rememberTablePage(tableId: string, page: number, scope = ''): void {
		this.tablePages[this.tablePageKey(tableId, scope)] = {
			page: Math.max(1, page),
			expiresAt: Date.now() + TABLE_PAGE_TTL_MS,
		};
	}

	resetTablePage(tableId: string, scope = ''): void {
		delete this.tablePages[this.tablePageKey(tableId, scope)];
	}

	clearTablePages(): void {
		this.tablePages = {};
	}

	private tablePageKey(tableId: string, scope: string): string {
		return [
			this.user?.id ?? 'anonymous',
			this.workspaceContext?.active_workspace_id ?? 'global',
			tableId,
			scope,
		].join('|');
	}
}

export function createAppState(): AppState {
	const state = new AppState();
	setContext(APP_STATE_CONTEXT, state);
	return state;
}

export function useAppState(): AppState {
	const state = getContext<AppState>(APP_STATE_CONTEXT);
	if (!state) throw new Error('App state has not been initialized');
	return state;
}
