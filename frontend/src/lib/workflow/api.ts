import { apiJSON } from "$lib/api/index.js";
import type {
  WorkflowCatalogAction,
  WorkflowCatalogState,
  WorkflowDetail,
  WorkflowSavePayload,
  WorkflowSummary,
} from "./types.js";

export const workflowApi = {
  async list(): Promise<WorkflowSummary[]> {
    const res = await apiJSON("/api/workflow");
    return (res.data ?? []) as WorkflowSummary[];
  },

  async get(id: string): Promise<WorkflowDetail> {
    const res = await apiJSON(`/api/workflow/${id}`);
    return res.data as WorkflowDetail;
  },

  async listStates(): Promise<WorkflowCatalogState[]> {
    const res = await apiJSON("/api/workflow/states");
    return (res.data ?? []) as WorkflowCatalogState[];
  },

  async listActions(): Promise<WorkflowCatalogAction[]> {
    const res = await apiJSON("/api/workflow/actions");
    return (res.data ?? []) as WorkflowCatalogAction[];
  },

  async createState(label: string): Promise<WorkflowCatalogState> {
    const res = await apiJSON("/api/workflow/states", {
      method: "POST",
      body: JSON.stringify({ label }),
    });
    return res.data as WorkflowCatalogState;
  },

  async createAction(label: string): Promise<WorkflowCatalogAction> {
    const res = await apiJSON("/api/workflow/actions", {
      method: "POST",
      body: JSON.stringify({ label }),
    });
    return res.data as WorkflowCatalogAction;
  },

  async create(payload: WorkflowSavePayload): Promise<{ id: string }> {
    const res = await apiJSON("/api/workflow", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    return res.data as { id: string };
  },

  async update(id: string, payload: WorkflowSavePayload): Promise<void> {
    await apiJSON(`/api/workflow/${id}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    });
  },

  async remove(id: string): Promise<void> {
    await apiJSON(`/api/workflow/${id}`, { method: "DELETE" });
  },
};
