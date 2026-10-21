<script lang="ts">
  import { onMount } from "svelte";
  import * as Table from "$lib/components/ui/table/index.js";
  import * as Dialog from "$lib/components/ui/dialog/index.js";
  import { Button } from "$lib/components/ui/button/index.js";
  import { Badge } from "$lib/components/ui/badge/index.js";
  import { Spinner } from "$lib/components/ui/spinner/index.js";
  import * as Empty from "$lib/components/ui/empty/index.js";
  import { apiJSON } from "$lib/api/index.js";
  import { toast } from "$lib/notifications";
  import GitBranchIcon from "@lucide/svelte/icons/git-branch";

  interface Workflow {
    id: string;
    name: string;
    target_entity: string;
    is_active: boolean;
  }

  let workflows = $state<Workflow[]>([]);
  let loading = $state(true);
  let deleteDialogOpen = $state(false);
  let workflowToDelete = $state<string | null>(null);

  async function loadWorkflows() {
    loading = true;
    try {
      const data = await apiJSON("/api/workflow");
      workflows = data.data || [];
    } catch (error) {
      console.error("Failed to load workflows:", error);
    } finally {
      loading = false;
    }
  }

  function openDeleteDialog(workflowId: string) {
    workflowToDelete = workflowId;
    deleteDialogOpen = true;
  }

  async function confirmDelete() {
    if (!workflowToDelete) return;
    try {
      await apiJSON(`/api/workflow/${workflowToDelete}`, { method: "DELETE" });
      toast.success("Workflow deleted successfully");
      await loadWorkflows();
    } catch (error) {
      console.error("Failed to delete workflow:", error);
      toast.error("Failed to delete workflow");
    } finally {
      deleteDialogOpen = false;
      workflowToDelete = null;
    }
  }

  onMount(() => {
    loadWorkflows();
  });
</script>

<div class="flex flex-col gap-6">
  <div class="flex items-center justify-between">
    <div>
      <h1 class="text-2xl font-bold tracking-tight">Workflows</h1>
      <p class="text-sm text-base-content/60">
        Manage entity-specific workflows
      </p>
    </div>
    <Button href="/workflow/new">New Workflow</Button>
  </div>

  <div class="border rounded-xl">
    {#if loading}
      <div class="flex items-center justify-center py-12">
        <Spinner class="size-8" />
      </div>
    {:else if workflows.length > 0}
      <div class="overflow-x-auto">
        <Table.Root>
          <Table.Header>
            <Table.Row>
              <Table.Head>Name</Table.Head>
              <Table.Head>Target Entity</Table.Head>
              <Table.Head>Status</Table.Head>
              <Table.Head class="text-right">Actions</Table.Head>
            </Table.Row>
          </Table.Header>
          <Table.Body>
            {#each workflows as workflow (workflow.id)}
              <Table.Row>
                <Table.Cell class="font-medium">{workflow.name}</Table.Cell>
                <Table.Cell class="text-base-content/60"
                  >{workflow.target_entity}</Table.Cell
                >
                <Table.Cell>
                  <Badge variant={workflow.is_active ? "default" : "secondary"}>
                    {workflow.is_active ? "Active" : "Inactive"}
                  </Badge>
                </Table.Cell>
                <Table.Cell class="text-right">
                  <Button
                    variant="ghost"
                    size="sm"
                    href={`/workflow/${workflow.id}`}>Edit</Button
                  >
                  <Button
                    variant="ghost"
                    size="sm"
                    onclick={() => openDeleteDialog(workflow.id)}>Delete</Button
                  >
                </Table.Cell>
              </Table.Row>
            {/each}
          </Table.Body>
        </Table.Root>
      </div>
    {:else}
      <Empty.Root class="py-16">
        <Empty.Media variant="icon">
          <GitBranchIcon />
        </Empty.Media>
        <Empty.Header>
          <Empty.Title>No workflows found</Empty.Title>
          <Empty.Description
            >Create a workflow to get started.</Empty.Description
          >
        </Empty.Header>
      </Empty.Root>
    {/if}
  </div>

  <Dialog.Root bind:open={deleteDialogOpen}>
    <Dialog.Content>
      <Dialog.Header>
        <Dialog.Title>Delete Workflow</Dialog.Title>
        <Dialog.Description>
          Are you sure you want to delete this workflow? This action cannot be
          undone.
        </Dialog.Description>
      </Dialog.Header>
      <Dialog.Footer>
        <Button variant="outline" onclick={() => (deleteDialogOpen = false)}>
          Cancel
        </Button>
        <Button variant="destructive" onclick={confirmDelete}>Delete</Button>
      </Dialog.Footer>
    </Dialog.Content>
  </Dialog.Root>
</div>
