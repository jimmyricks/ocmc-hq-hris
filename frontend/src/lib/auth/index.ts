import { writable } from 'svelte/store';
import { browser } from '$app/environment';
import { get } from 'svelte/store';
import { clearActiveWorkspaceId } from '$lib/workspaces/context';

export interface User {
	id: string;
	username: string;
	email: string;
	full_name: string;
	is_superuser: boolean;
	roles: string[];
}

export interface AuthState {
	token: string | null;
	refreshToken: string | null;
	user: User | null;
}

function loadToken(): string | null {
	if (!browser) return null;
	return localStorage.getItem('token');
}

function loadRefreshToken(): string | null {
	if (!browser) return null;
	return localStorage.getItem('refresh_token');
}

function loadUser(): User | null {
	if (!browser) return null;
	try {
		const raw = localStorage.getItem('user');
		return raw ? (JSON.parse(raw) as User) : null;
	} catch {
		return null;
	}
}

export const auth = writable<AuthState>({
	token: loadToken(),
	refreshToken: loadRefreshToken(),
	user: loadUser()
});

export function setAuth(token: string, user: User, refreshToken?: string) {
	clearActiveWorkspaceId();
	if (browser) {
		localStorage.setItem('token', token);
		localStorage.setItem('user', JSON.stringify(user));
		if (refreshToken) localStorage.setItem('refresh_token', refreshToken);
	}
	auth.set({ token, refreshToken: refreshToken ?? null, user });
}

export function setToken(token: string) {
	if (browser) localStorage.setItem('token', token);
	auth.update((s) => ({ ...s, token }));
}

export function setUser(user: User) {
	if (browser) localStorage.setItem('user', JSON.stringify(user));
	auth.update((s) => ({ ...s, user }));
}

export function clearAuth() {
	clearActiveWorkspaceId();
	if (browser) {
		localStorage.removeItem('token');
		localStorage.removeItem('refresh_token');
		localStorage.removeItem('user');
	}
	auth.set({ token: null, refreshToken: null, user: null });
}

export function getToken(): string | null {
	if (browser) return localStorage.getItem('token');
	return get(auth).token;
}

export function getRefreshToken(): string | null {
	if (browser) return localStorage.getItem('refresh_token');
	return get(auth).refreshToken;
}

export function getUser(): User | null {
	if (browser) return loadUser();
	return get(auth).user;
}

export function isProjectManager(user: User | null): boolean {
	if (!user) return false;
	if (user.is_superuser) return true;
	const managerRoles = ['ProjectManager', 'SystemManager', 'Administrator'];
	return user.roles.some((role) => managerRoles.includes(role));
}
