<script lang="ts">
  import { page } from "$app/state";
  import { goto } from "$app/navigation";
  import { onMount } from "svelte";
  import { loadEntity, saveEntity } from "$lib/api/index.js";
  import { getToken } from "$lib/auth";
  import { Button } from "$lib/components/ui/button/index.js";
  import MetadataDataTable, {
    type EntityMetaSvelte,
  } from "$lib/components/metadata-data-table.svelte";
  import EntityRecordModal from "$lib/components/entity-record-modal.svelte";
  import type { ModalMode } from "$lib/components/entity-record-modal.svelte";
  import { toast } from "svelte-sonner";

  let entityName = $derived(page.params.entity);
  let createFromQuery = $derived(page.url.searchParams.get("create") === "1");
  let meta = $state<EntityMetaSvelte | null>(null);
  let records = $state<Record<string, any>[]>([]);
  let loading = $state(true);
  let error = $state("");
  let modalOpen = $state(false);
  let modalMode = $state<ModalMode>("view");
  let selectedRecord = $state<Record<string, any> | null>(null);
  let saving = $state(false);

  $effect(() => {
    const name = entityName ?? "";
    if (!getToken()) {
      goto("/login");
      return;
    }
    if (!name) {
      loading = false;
      return;
    }
    loading = true;
    error = "";
    async function load() {
      try {
        const result = await loadEntity(name);
        meta = result.meta;
        records = result.records;
      } catch (err: any) {
        error = err.message;
      } finally {
        loading = false;
      }
    }
    load();
  });

  function openCreate() {
    selectedRecord = {};
    modalMode = "create";
    modalOpen = true;
    if (createFromQuery) {
      goto(page.url.pathname, { replaceState: true });
    }
  }

  onMount(() => {
    if (createFromQuery) {
      openCreate();
    }
  });

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
    if (!entityName) return;
    saving = true;
    try {
      const recordId = modalMode === "edit" ? selectedRecord?.id : undefined;
      const result = await saveEntity(entityName, data, recordId);
      if (result.status === "success") {
        toast.success(
          modalMode === "create"
            ? "Record created successfully"
            : "Record updated successfully",
        );
        await reload();
        closeModal();
      } else {
        toast.error(result.message || "Failed to save record");
      }
    } catch (err: any) {
      toast.error(err.message || "Failed to save record");
    } finally {
      saving = false;
    }
  }

  async function reload() {
    if (!entityName) return;
    const result = await loadEntity(entityName, 1, 20);
    records = result.records;
  }
</script>

<main class="flex flex-col gap-6">
  <div class="flex items-center justify-between">
    <h1 class="text-2xl font-bold tracking-tight">
      {meta?.label || entityName}
    </h1>
    <Button onclick={openCreate}>Create</Button>
  </div>

  {#if loading}
    <p class="text-muted-foreground">Loading records...</p>
  {:else if error}
    <p class="rounded-md bg-destructive/10 p-3 text-sm text-destructive">
      {error}
    </p>
  {:else if meta}
    <MetadataDataTable {meta} data={records} onRowClick={openEdit} />
  {/if}

  <EntityRecordModal
    bind:open={modalOpen}
    mode={modalMode}
    {meta}
    {entityName}
    recordId={selectedRecord?.id}
    record={selectedRecord}
    {saving}
    onClose={closeModal}
    onSave={handleSave}
  />
</main>
