<script lang="ts">
  import { onMount } from "svelte";
  import { apiJSON, toPaginatedResult } from "$lib/api/index.js";
  import { toast } from "$lib/notifications";
  import { useAppState } from "$lib/app-state.svelte.js";
  import Pagination from "$lib/components/pagination.svelte";
  import GitBranchIcon from "@lucide/svelte/icons/git-branch";

  import type { WorkflowSummary as Workflow } from "$lib/workflow/types";

  const appState = useAppState();
  let workflows = $state<Workflow[]>([]);
  let workflowsPage = $state(appState.tablePage("workflows"));
  let workflowsPageSize = $state(25);
  let workflowsTotal = $state(0);
  let loading = $state(true);
  let workflowToDelete = $state<string | null>(null);
  let deleteDialog = $state<HTMLDialogElement>();

  async function loadWorkflows(page = workflowsPage) {
    loading = true;
    try {
      const data = await apiJSON(
        `/api/workflow?page=${page}&page_size=${workflowsPageSize}`,
      );
      const result = toPaginatedResult<Workflow>(data, page, workflowsPageSize);
      if (!result.items.length && result.total > 0 && page > 1) {
        return loadWorkflows(Math.ceil(result.total / workflowsPageSize));
      }
      workflows = result.items;
      workflowsTotal = result.total;
      workflowsPage = result.page;
      appState.rememberTablePage("workflows", workflowsPage);
    } catch (error) {
      console.error("Failed to load workflows:", error);
    } finally {
      loading = false;
    }
  }

  async function makeDefault(workflowId: string) {
    try {
      await apiJSON(`/api/workflow/${workflowId}`, {
        method: "PUT",
        body: JSON.stringify({ is_default: true }),
      });
      toast.success("Default workflow updated");
      await loadWorkflows();
    } catch (error: any) {
      toast.error(error?.message || "Failed to update default workflow");
    }
  }

  function setWorkflowsPage(page: number) {
    workflowsPage = page;
    appState.rememberTablePage("workflows", page);
    void loadWorkflows(page);
  }

  function openDeleteDialog(workflowId: string) {
    workflowToDelete = workflowId;
    deleteDialog?.showModal();
  }

  async function confirmDelete() {
    if (!workflowToDelete) return;
    try {
      await apiJSON(`/api/workflow/${workflowToDelete}`, { method: "DELETE" });
      toast.success("Workflow deleted successfully");
      await loadWorkflows(workflowsPage);
    } catch (error) {
      console.error("Failed to delete workflow:", error);
      toast.error("Failed to delete workflow");
    } finally {
      workflowToDelete = null;
      deleteDialog?.close();
    }
  }

  onMount(() => {
    void loadWorkflows(workflowsPage);
  });
</script>

<div class="flex flex-col gap-6">
  <div class="flex flex-wrap items-end justify-between gap-4">
    <div>
      <h1 class="text-2xl font-bold tracking-tight">Workflows</h1>
      <p class="mt-1 text-sm text-base-content/60">
        Manage entity-specific workflows
      </p>
    </div>
    <a class="btn btn-primary" href="/workflow/new">New Workflow</a>
  </div>

  <section class="card bg-base-100 shadow-sm overflow-hidden">
    {#if loading}
      <div class="flex items-center justify-center py-12">
        <span
          class="loading loading-spinner loading-lg text-primary"
          role="status"
          aria-label="Loading"
        ></span>
      </div>
    {:else if workflows.length > 0}
      <div class="overflow-x-auto">
        <table class="table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Target Entity</th>
              <th>Scope</th>
              <th>Default</th>
              <th>Status</th>
              <th class="text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {#each workflows as workflow (workflow.id)}
              <tr>
                <td class="font-medium">{workflow.name}</td>
                <td class="text-base-content/60">{workflow.target_entity}</td>
                <td class="text-base-content/60"
                  >{workflow.workspace_name || "Global"}</td
                >
                <td>
                  {#if workflow.is_default}
                    <span class="badge badge-soft badge-success">Default</span>
                  {:else}
                    <button
                      type="button"
                      class="btn btn-ghost btn-sm"
                      onclick={() => makeDefault(workflow.id)}
                    >
                      Set default
                    </button>
                  {/if}
                </td>
                <td>
                  <span
                    class={workflow.is_active
                      ? "badge badge-soft badge-success"
                      : "badge badge-soft badge-neutral"}
                  >
                    {workflow.is_active ? "Active" : "Inactive"}
                  </span>
                </td>
                <td class="text-right">
                  <a
                    class="btn btn-ghost btn-sm"
                    href={`/workflow/${workflow.id}`}>Edit</a
                  >
                  <button
                    type="button"
                    class="btn btn-ghost btn-sm"
                    onclick={() => openDeleteDialog(workflow.id)}>Delete</button
                  >
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
      <Pagination
        page={workflowsPage}
        pageSize={workflowsPageSize}
        total={workflowsTotal}
        {loading}
        pageSizeOptions={[10, 25, 50, 100]}
        onchange={setWorkflowsPage}
        onpagesizechange={(size) => {
          workflowsPageSize = size;
          setWorkflowsPage(1);
        }}
      />
    {:else}
      <div class="grid justify-items-center gap-2 py-16 text-center">
        <GitBranchIcon class="size-8 text-base-content/40" />
        <h2 class="text-base font-semibold">No workflows found</h2>
        <p class="text-sm text-base-content/60">
          Create a workflow to get started.
        </p>
      </div>
    {/if}
  </section>

  <dialog bind:this={deleteDialog} class="modal">
    <div class="modal-box">
      <h3 class="text-lg font-bold">Delete Workflow</h3>
      <p class="py-4 text-sm text-base-content/70">
        Are you sure you want to delete this workflow? This action cannot be
        undone.
      </p>
      <form method="dialog" class="modal-action">
        <button class="btn">Cancel</button>
        <button
          type="button"
          class="btn btn-soft btn-error"
          onclick={confirmDelete}>Delete</button
        >
      </form>
    </div>
    <form method="dialog" class="modal-backdrop">
      <button aria-label="Close dialog">close</button>
    </form>
  </dialog>
</div>
