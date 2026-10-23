/**
 * Simple in-memory cache for reference/lookup data (users, task_types,
 * task_categories, projects) that multiple pages need but rarely changes.
 *
 * Each entry is fetched once per page session and reused. Call `invalidate()`
 * after a create/update/delete to force a re-fetch on next access.
 */
import { taskApi } from "./api.js";
import type { Project, TaskCategory, TaskType, User } from "./types.js";
import { getActiveWorkspaceId } from "$lib/workspaces/context";
import { getUser } from "$lib/auth";

type Entry<T> = { promise: Promise<T> } | { value: T } | undefined;

const _cache: Record<string, Entry<any>> = {};
const sessionCacheKey = (key: string) =>
	`${key}:${getUser()?.id ?? "anonymous"}:${getActiveWorkspaceId() ?? "global"}`;

async function getOrFetch<T>(key: string, fetcher: () => Promise<T>): Promise<T> {
	const entry = _cache[key];
	if (entry) {
		if ("promise" in entry) return entry.promise;
		return entry.value;
	}
	const pending = { promise: fetcher() };
	_cache[key] = pending;
	try {
		const value = await pending.promise;
		if (_cache[key] === pending) _cache[key] = { value };
		return value;
	} catch (err) {
		if (_cache[key] === pending) delete _cache[key];
		throw err;
	}
}

export const refCache = {
	async getUsers(): Promise<User[]> {
		return getOrFetch(sessionCacheKey("users"), () => taskApi.getUsers());
	},

	async getTaskTypes(): Promise<TaskType[]> {
		return getOrFetch(sessionCacheKey("task_types"), () => taskApi.getTaskTypes());
	},

	async getTaskCategories(): Promise<TaskCategory[]> {
		return getOrFetch(sessionCacheKey("task_categories"), () => taskApi.getTaskCategories());
	},

	async getProjects(): Promise<Project[]> {
		return getOrFetch(sessionCacheKey("projects"), () => taskApi.getProjects());
	},

	/** Invalidate one key or the entire cache. */
	invalidate(key?: "users" | "task_types" | "task_categories" | "projects") {
		if (key) {
			for (const cacheKey of Object.keys(_cache)) {
				if (cacheKey.startsWith(`${key}:`)) delete _cache[cacheKey];
			}
		}
		else for (const k of Object.keys(_cache)) delete _cache[k];
	},
};
