import { apiJSON } from "$lib/api/index.js";
import type { User } from "$lib/task-manager/types.js";

export const userApi = {
  async lookup(options: {
    search?: string;
    projectId?: string;
    pageSize?: number;
  } = {}): Promise<User[]> {
    const params = new URLSearchParams({
      page_size: String(options.pageSize ?? 20),
    });
    if (options.search?.trim()) params.set("search", options.search.trim());
    if (options.projectId) params.set("project_id", options.projectId);

    const response = await apiJSON(`/api/workspaces/directory?${params}`);
    return (response.data ?? []) as User[];
  },
};
