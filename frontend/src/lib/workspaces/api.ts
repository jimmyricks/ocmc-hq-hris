import { apiJSON } from "$lib/api";
import type { PlannerActivity, WorkspaceContext } from "./types";
export { getActiveWorkspaceId, setActiveWorkspaceId } from "./context";

export const workspaceApi = {
  async getContext(): Promise<WorkspaceContext> {
    const res = await apiJSON("/api/workspaces/context");
    return res.data as WorkspaceContext;
  },

  async select(workspaceId: string | null): Promise<void> {
    await apiJSON("/api/workspaces/context", {
      method: "POST",
      body: JSON.stringify({ workspace_id: workspaceId }),
    });
  },

  async getUnmapped() {
    const res = await apiJSON("/api/workspaces/unmapped");
    return res.data as {
      projects: Array<{ id: string; name: string }>;
      task_types: Array<{ id: string; name: string; unit_rate: number; unit: string }>;
    };
  },

  async assignMember(
    workspaceId: string,
    userId: string,
    membershipRole: "member" | "supervisor",
    isHome: boolean,
  ): Promise<void> {
    await apiJSON(`/api/workspaces/${workspaceId}/memberships`, {
      method: "POST",
      body: JSON.stringify({
        user_id: userId,
        membership_role: membershipRole,
        is_home: isHome,
      }),
    });
  },

  async getMembers(workspaceId: string) {
    const res = await apiJSON(`/api/workspaces/${workspaceId}/memberships`);
    return (res.data ?? []) as Array<{
      id: string;
      user_id: string;
      membership_role: "member" | "supervisor";
      is_home: boolean;
    }>;
  },

  async removeMember(workspaceId: string, membershipId: string): Promise<void> {
    await apiJSON(
      `/api/workspaces/${workspaceId}/memberships/${membershipId}`,
      { method: "DELETE" },
    );
  },

  async mapLegacy(
    entity: "project" | "task_type",
    recordId: string,
    workspaceId: string,
  ): Promise<void> {
    await apiJSON("/api/workspaces/map-legacy", {
      method: "POST",
      body: JSON.stringify({
        entity,
        record_id: recordId,
        workspace_id: workspaceId,
      }),
    });
  },

  async updateWorkspace(
    workspaceId: string,
    data: { color?: string; timezone?: string; is_active?: boolean },
  ): Promise<void> {
    await apiJSON(`/api/workspaces/${workspaceId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  },

  async getTeams(workspaceId: string) {
    const res = await apiJSON(`/api/workspaces/${workspaceId}/teams`);
    return (res.data ?? []) as Array<{
      id: string;
      workspace_id: string;
      name: string;
      slug: string;
    }>;
  },

  async getResources(workspaceId?: string) {
    const params = new URLSearchParams();
    if (workspaceId) params.set("workspace_id", workspaceId);
    const query = params.size ? `?${params}` : "";
    const res = await apiJSON(`/api/planner/resources${query}`);
    return (res.data ?? []) as Array<{
      id: string;
      workspace_id: string;
      name: string;
      resource_type: string;
    }>;
  },

  async createResource(payload: {
    workspace_id: string;
    name: string;
    resource_type: "room" | "equipment" | "instructor" | "other";
    description?: string;
  }) {
    return apiJSON("/api/planner/resources", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async updateResource(
    resourceId: string,
    data: { name?: string; is_active?: boolean },
  ) {
    return apiJSON(`/api/planner/resources/${resourceId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  },

  async createEvent(payload: Record<string, unknown>) {
    return apiJSON("/api/planner/events", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async createSeries(payload: Record<string, unknown>) {
    return apiJSON("/api/planner/series", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async getPlannerActivities(
    start: string,
    end: string,
    projectId?: string,
  ): Promise<PlannerActivity[]> {
    const params = new URLSearchParams({ start, end });
    if (projectId) params.set("project_id", projectId);
    const pageSize = 500;
    const activities: PlannerActivity[] = [];
    let page = 1;
    let total = 0;
    do {
      params.set("page", String(page));
      params.set("page_size", String(pageSize));
      const res = await apiJSON(`/api/planner/activities?${params}`);
      activities.push(...((res.data ?? []) as PlannerActivity[]));
      total = res.total ?? activities.length;
      page += 1;
    } while (activities.length < total);
    return activities;
  },
};
