<script lang="ts">
  import { browser } from "$app/environment";
  import { toast } from "svelte-sonner";
  import { loadEntity, saveEntity, deleteEntity } from "$lib/api/index.js";
  import { refCache } from "$lib/task-manager/ref-cache.js";
  import type { EntityMetaSvelte } from "$lib/components/metadata-data-table.svelte";
  import EntityRecordModal from "$lib/components/entity-record-modal.svelte";
  import type { ModalMode } from "$lib/components/entity-record-modal.svelte";

  import { Button } from "$lib/components/ui/button/index.js";
  import MetadataDataTable from "$lib/components/metadata-data-table.svelte";
  import PlusIcon from "@lucide/svelte/icons/plus";

  // ── State ────────────────────────────────────────────────────────────
  let meta = $state<EntityMetaSvelte | null>(null);
  let records = $state<Record<string, any>[]>([]);
  let loading = $state(true);
  let error = $state("");

  let modalOpen = $state(false);
  let modalMode = $state<ModalMode>("create");
  let selectedRecord = $state<Record<string, any> | null>(null);
  let saving = $state(false);

  // ── Lifecycle ────────────────────────────────────────────────────────
  $effect(() => {
    if (!browser) return;
    loadData();
  });

  async function loadData() {
    loading = true;
    error = "";
    try {
      const result = await loadEntity("task_type", 1, 100);
      meta = result.meta as EntityMetaSvelte;
      records = result.records;
    } catch (err: any) {
      error = err.message || "Failed to load task types";
    } finally {
      loading = false;
    }
  }

  function openCreate() {
    selectedRecord = {};
    modalMode = "create";
    modalOpen = true;
  }

  function openEdit(record: Record<string, any>) {
    selectedRecord = record;
    modalMode = "edit";
    modalOpen = true;
  }

  function closeModal() {
    modalOpen = false;
    selectedRecord = null;
  }

  async function handleSave(data: Record<string, any>) {
    saving = true;
    try {
      const recordId = modalMode === "edit" ? selectedRecord?.id : undefined;
      await saveEntity("task_type", data, recordId);
      toast.success(
        modalMode === "create" ? "Task type created" : "Task type updated",
      );
      await loadData();
      refCache.invalidate("task_types");
      closeModal();
    } catch (err: any) {
      toast.error(err.message || "Failed to save task type");
    } finally {
      saving = false;
    }
  }

  async function handleDelete() {
    if (!selectedRecord?.id) return;
    if (!confirm("Delete this task type?")) return;

    saving = true;
    try {
      await deleteEntity("task_type", selectedRecord.id);
      toast.success("Task type deleted");
      await loadData();
      refCache.invalidate("task_types");
      closeModal();
    } catch (err: any) {
      toast.error(err.message || "Failed to delete task type");
    } finally {
      saving = false;
    }
  }
</script>

<div class="flex flex-col gap-6">
  <div
    class="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between"
  >
    <div>
      <h1 class="text-2xl font-bold tracking-tight">Tasks & Rates</h1>
      <p class="text-sm text-muted-foreground">
        Manage task types and their pay rates.
      </p>
    </div>
    <Button onclick={openCreate}>
      <PlusIcon data-icon="inline-start" />
      Add Task Type
    </Button>
  </div>

  {#if error}
    <p class="rounded-md bg-destructive/10 p-3 text-sm text-destructive">
      {error}
    </p>
  {/if}

  {#if meta}
    <MetadataDataTable {meta} data={records} onRowClick={openEdit} />
  {:else if loading}
    <p class="text-muted-foreground">Loading task types...</p>
  {/if}
</div>

<EntityRecordModal
  bind:open={modalOpen}
  mode={modalMode}
  {meta}
  entityName="task_type"
  recordId={selectedRecord?.id}
  record={selectedRecord}
  {saving}
  onClose={closeModal}
  onSave={handleSave}
  onDelete={handleDelete}
/>
