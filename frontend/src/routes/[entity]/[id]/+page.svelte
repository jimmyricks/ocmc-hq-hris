<script lang="ts">
  import { page } from "$app/state";
  import { goto } from "$app/navigation";
  import {
    getEntityMeta,
    getEntityRecord,
    saveEntity,
  } from "$lib/api/index.js";
  import { getToken } from "$lib/auth";
  import { ChevronLeft } from "@lucide/svelte";
  import { Button } from "$lib/components/ui/button/index.js";
  import EntityRecordModal from "$lib/components/entity-record-modal.svelte";
  import type { EntityMetaSvelte } from "$lib/components/metadata-data-table.svelte";
  import type { ModalMode } from "$lib/components/entity-record-modal.svelte";
  import { toast } from "svelte-sonner";

  let entityName = $derived(page.params.entity);
  let recordId = $derived(page.params.id);
  let meta = $state<EntityMetaSvelte | null>(null);
  let record = $state<Record<string, any> | null>(null);
  let loading = $state(true);
  let error = $state("");
  let modalOpen = $state(true);
  let mode = $state<ModalMode>("view");
  let saving = $state(false);

  $effect(() => {
    const entity = entityName ?? "";
    const id = recordId ?? "";
    if (!getToken()) {
      goto("/login");
      return;
    }
    if (!entity || !id) {
      loading = false;
      return;
    }
    loading = true;
    error = "";
    async function load() {
      try {
        const [metaRes, recordRes] = await Promise.all([
          getEntityMeta(entity),
          getEntityRecord(entity, id),
        ]);
        meta = metaRes.data || null;
        record = recordRes.data || null;
      } catch (err: any) {
        error = err.message;
      } finally {
        loading = false;
      }
    }
    load();
  });

  function handleClose() {
    goto(`/${entityName}`);
  }

  function handleEdit() {
    mode = "edit";
  }

  async function handleSave(data: Record<string, any>) {
    if (!entityName) return;
    saving = true;
    try {
      const result = await saveEntity(entityName, data, recordId);
      if (result.status === "success") {
        toast.success("Record saved successfully");
        record = result.data || record;
        mode = "view";
      } else {
        toast.error(result.message || "Failed to save record");
      }
    } catch (err: any) {
      toast.error(err.message || "Failed to save record");
    } finally {
      saving = false;
    }
  }

  function handleWorkflow() {
    toast.info("Workflow action triggered");
  }

  function handleDelete() {
    toast.info("Delete action triggered");
  }
</script>

<main class="flex flex-col gap-6">
  <div class="flex items-center gap-2 text-sm text-muted-foreground">
    <a href="/{entityName}" class="inline-flex items-center hover:text-primary">
      <ChevronLeft class="size-4" />
      {meta?.label || entityName}
    </a>
    <span>/</span>
    <span class="font-medium text-card-foreground">{recordId}</span>
  </div>

  <h1 class="text-2xl font-bold tracking-tight">
    {meta?.label || entityName} - {recordId}
  </h1>

  {#if error}
    <p class="rounded-md bg-destructive/10 p-3 text-sm text-destructive">
      {error}
    </p>
  {:else}
    <EntityRecordModal
      bind:open={modalOpen}
      {mode}
      {meta}
      {entityName}
      {recordId}
      {record}
      {loading}
      {saving}
      onClose={handleClose}
      onEdit={handleEdit}
      onSave={handleSave}
      onWorkflow={handleWorkflow}
      onDelete={handleDelete}
    />
  {/if}
</main>
