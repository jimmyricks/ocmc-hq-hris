<script lang="ts">
  import { Button } from "$lib/components/ui/button/index.js";
  import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
  } from "$lib/components/ui/dialog/index.js";
  import type { EntityMetaSvelte } from "$lib/components/metadata-data-table.svelte";
  import EntityFormRenderer from "$lib/components/entity-form-renderer.svelte";
  import { getEntityMeta, listEntity } from "$lib/api/index.js";
  import SaveIcon from "@lucide/svelte/icons/save";
  import Trash2Icon from "@lucide/svelte/icons/trash-2";

  export type ModalMode = "view" | "edit" | "create";

  interface Props {
    open?: boolean;
    mode?: ModalMode;
    meta: EntityMetaSvelte | null;
    entityName: string | undefined;
    recordId?: string | undefined;
    record?: Record<string, any> | null;
    loading?: boolean;
    saving?: boolean;
    onClose?: () => void;
    onSave?: (data: Record<string, any>) => void;
    onEdit?: () => void;
    onWorkflow?: () => void;
    onDelete?: () => void;
  }

  let {
    open = $bindable(false),
    mode = "view",
    meta,
    entityName,
    recordId,
    record = {},
    loading = false,
    saving = false,
    onClose,
    onSave,
    onEdit,
    onWorkflow,
    onDelete,
  }: Props = $props();

  let isEditing = $derived(mode === "edit" || mode === "create");
  let title = $derived(
    mode === "create"
      ? `Create ${meta?.label || entityName}`
      : mode === "edit"
        ? `Edit ${meta?.label || entityName}`
        : `${meta?.label || entityName} - ${recordId}`,
  );

  let formData = $state<Record<string, any>>({});
  let linkOptions = $state<Record<string, any[]>>({});

  $effect(() => {
    const initial = record ? { ...record } : {};
    if (meta) {
      for (const field of meta.fields) {
        if (
          !(field.key in initial) &&
          field.default !== undefined &&
          field.default !== null
        ) {
          initial[field.key] = field.default;
        }
      }
    }
    formData = initial;
  });

  $effect(() => {
    if (open && meta) {
      loadLinkOptions();
    }
  });

  async function loadLinkOptions() {
    if (!meta) return;
    const linkEntities = [
      ...new Set(
        meta.fields
          .filter((field) => field.link_entity && !field.hidden)
          .map((field) => field.link_entity as string),
      ),
    ];
    if (linkEntities.length === 0) return;

    const next: Record<string, any[]> = {};
    await Promise.all(
      linkEntities.map(async (entityName) => {
        try {
          const [metaRes, listRes] = await Promise.all([
            getEntityMeta(entityName),
            listEntity(entityName, 1, 100),
          ]);
          const titleField = metaRes.data?.title_field || "name";
          next[entityName] = (listRes.data || []).map((record: any) => ({
            value: record.id,
            label:
              record[titleField] ||
              record.name ||
              record.title ||
              record.full_name ||
              record.id,
          }));
        } catch (err) {
          console.error(`Failed to load link options for ${entityName}:`, err);
          next[entityName] = [];
        }
      }),
    );
    linkOptions = next;
  }

  function handleSave() {
    const clean = { ...formData };
    for (const key of Object.keys(clean)) {
      if (key.startsWith("_")) {
        delete clean[key];
      }
    }

    if (meta) {
      // Drop hidden, readonly, and system-managed fields so the payload only
      // contains writable values the backend expects.
      for (const field of meta.fields) {
        if (field.key === "id" || field.hidden || field.readonly) {
          delete clean[field.key];
        }
      }

      // Optional date / datetime fields with an empty string must be omitted;
      // Pydantic rejects '' for Optional[date] / Optional[datetime].
      for (const field of meta.fields) {
        if (
          (field.type === "date" || field.type === "datetime") &&
          !field.required &&
          clean[field.key] === ""
        ) {
          delete clean[field.key];
        }
      }
    }

    onSave?.(clean);
  }

  function handleClose() {
    open = false;
    onClose?.();
  }
</script>

<Dialog bind:open>
  <DialogContent class="max-h-[90vh] overflow-y-auto !max-w-xl p-4!">
    <DialogHeader>
      <DialogTitle class="text-xl">{title}</DialogTitle>
      <DialogDescription>
        {#if mode === "view"}
          View {meta?.label || entityName} record details
        {:else if mode === "create"}
          Fill in the details to create a new {meta?.label || entityName}
        {:else}
          Update the {meta?.label || entityName} record details
        {/if}
      </DialogDescription>
    </DialogHeader>

    <form
      onsubmit={(e) => {
        e.preventDefault();
        handleSave();
      }}
      class="contents"
    >
      {#if loading}
        <div class="py-8 text-center text-muted-foreground">
          Loading record...
        </div>
      {:else if meta}
        <EntityFormRenderer
          bind:formData
          {meta}
          disabled={!isEditing}
          {linkOptions}
          {entityName}
          {recordId}
        />
      {:else}
        <div class="py-8 text-center text-muted-foreground">
          No metadata available.
        </div>
      {/if}

      <DialogFooter class="gap-2">
        {#if mode === "view"}
          <Button variant="outline" onclick={handleClose} class="h-9">
            Close
          </Button>
          {#if onWorkflow}
            <Button variant="secondary" onclick={onWorkflow} class="h-9">
              Workflow
            </Button>
          {/if}
          {#if onEdit}
            <Button onclick={onEdit} class="h-9">Edit</Button>
          {/if}
          {#if onDelete}
            <Button
              variant="outline"
              onclick={onDelete}
              class="h-9 gap-1.5 text-destructive hover:text-destructive hover:bg-destructive/10"
            >
              <Trash2Icon class="size-4" />
              Delete
            </Button>
          {/if}
        {:else}
          <div class="flex w-full justify-end gap-2">
            <Button
              type="button"
              variant="outline"
              onclick={handleClose}
              class="h-9"
            >
              Cancel
            </Button>
            <Button type="submit" disabled={saving} class="h-9 gap-1.5">
              <SaveIcon class="size-4" />
              {saving ? "Saving..." : mode === "create" ? "Create" : "Save"}
            </Button>
          </div>
        {/if}
      </DialogFooter>
    </form>
  </DialogContent>
</Dialog>
