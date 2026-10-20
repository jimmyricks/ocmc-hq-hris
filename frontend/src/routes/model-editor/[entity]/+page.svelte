<script lang="ts">
  import { onMount } from "svelte";
  import { page } from "$app/state";
  import { Button } from "$lib/components/ui/button/index.js";
  import { Badge } from "$lib/components/ui/badge/index.js";
  import { Input } from "$lib/components/ui/input/index.js";
  import { Textarea } from "$lib/components/ui/textarea/index.js";
  import * as Item from "$lib/components/ui/item/index.js";
  import * as Tabs from "$lib/components/ui/tabs/index.js";
  import * as Select from "$lib/components/ui/select/index.js";
  import * as Field from "$lib/components/ui/field/index.js";
  import * as Dialog from "$lib/components/ui/dialog/index.js";
  import { Switch } from "$lib/components/ui/switch/index.js";
  import ArrowLeftIcon from "@lucide/svelte/icons/arrow-left";
  import SaveIcon from "@lucide/svelte/icons/save";
  import XIcon from "@lucide/svelte/icons/x";
  import CheckIcon from "@lucide/svelte/icons/check";
  import GripVerticalIcon from "@lucide/svelte/icons/grip-vertical";
  import PlusIcon from "@lucide/svelte/icons/plus";
  import Trash2Icon from "@lucide/svelte/icons/trash-2";
  import MousePointerClickIcon from "@lucide/svelte/icons/mouse-pointer-click";
  import { apiJSON } from "$lib/api/index.js";
  import { dndzone } from "svelte-dnd-action";

  let entityName = $derived(page.params.entity ?? "");
  let hasChanges = $state(false);
  let saving = $state(false);
  let showSaveConfirm = $state(false);
  let selectedField = $state<Field | null>(null);
  let selectedFieldIndex = $state<number | null>(null);
  let activeTab = $state("fields");

  const FIELD_TYPES = [
    { value: "string", label: "String" },
    { value: "text", label: "Text" },
    { value: "number", label: "Number" },
    { value: "integer", label: "Integer" },
    { value: "decimal", label: "Decimal" },
    { value: "datetime", label: "Date Time" },
    { value: "date", label: "Date" },
    { value: "time", label: "Time" },
    { value: "boolean", label: "Boolean" },
    { value: "select", label: "Select" },
    { value: "link", label: "Link" },
    { value: "parent_child_link", label: "Parent Child Link" },
    { value: "query_link", label: "Query Link" },
  ];

  interface Field {
    id: string;
    name: string;
    label: string;
    field_type: string;
    required: boolean;
    readonly: boolean;
    hidden: boolean;
    [key: string]: any;
  }

  interface EntityMetadata {
    name: string;
    label: string;
    module: string;
    fields: Field[];
    [key: string]: any;
  }

  let metadata = $state<EntityMetadata | null>(null);
  let originalMetadata = $state<EntityMetadata | null>(null);
  let metadataDiff = $state<
    Array<{ path: string; type: string; oldValue: any; newValue: any }>
  >([]);

  interface GroupedDiff {
    category: string;
    changes: Array<{
      path: string;
      type: string;
      oldValue: any;
      newValue: any;
    }>;
  }

  const groupedDiff = $derived.by(() => {
    const diffs = metadataDiff;
    if (!diffs.length) return [];

    const groups: Record<
      string,
      Array<{ path: string; type: string; oldValue: any; newValue: any }>
    > = {};
    const categoryLabels: Record<string, string> = {
      fields: "Fields",
      links: "Links",
      children: "Children",
      sections: "Sections",
    };

    for (const change of diffs) {
      const topKey = change.path.split(/[.[]/)[0] || "";
      const category = categoryLabels[topKey] || "General";
      if (!groups[category]) groups[category] = [];
      groups[category].push(change);
    }

    const order = ["General", "Fields", "Links", "Children", "Sections"];
    return order
      .filter((cat) => groups[cat])
      .map((cat) => ({ category: cat, changes: groups[cat]! }));
  });

  function formatValue(val: any): string {
    if (val === undefined) return "(none)";
    if (val === null) return "null";
    if (typeof val === "object") return JSON.stringify(val);
    return String(val);
  }

  function handleFieldReorder(e: CustomEvent<{ items: Field[] }>) {
    if (!metadata) return;
    metadata.fields = e.detail.items;
    hasChanges = true;
  }

  function selectField(field: Field, index: number) {
    selectedField = field;
    selectedFieldIndex = index;
  }

  function addField() {
    if (!metadata) return;
    const newField: Field = {
      id: `new_field_${Date.now()}`,
      name: `new_field_${metadata.fields.length + 1}`,
      label: "New Field",
      field_type: "string",
      required: false,
      readonly: false,
      hidden: false,
      in_list_view: true,
    };
    metadata.fields = [...metadata.fields, newField];
    selectedField = newField;
    selectedFieldIndex = metadata.fields.length - 1;
    hasChanges = true;
  }

  function removeField() {
    if (!metadata || selectedFieldIndex === null) return;
    metadata.fields = metadata.fields.filter(
      (_, i) => i !== selectedFieldIndex,
    );
    selectedField = null;
    selectedFieldIndex = null;
    hasChanges = true;
  }

  async function loadEntity() {
    try {
      const data = await apiJSON(
        `/api/admin/model-editor/entity/${entityName}`,
      );
      if (data.status === "success") {
        const rawMetadata = data.data?.metadata || data.data;
        // Add id property to fields for dndzone
        if (rawMetadata.fields) {
          rawMetadata.fields = rawMetadata.fields.map((field: Field) => ({
            ...field,
            id: field.name,
          }));
        }
        rawMetadata.field_layout = rawMetadata.field_layout || [];
        metadata = rawMetadata;
        originalMetadata = JSON.parse(JSON.stringify(metadata));
      }
    } catch (error) {
      console.error("Failed to load entity:", error);
    }
  }

  function cleanFieldLayout() {
    if (!metadata) return;
    metadata.field_layout = metadata.field_layout
      .map((row: string[]) => row.filter((f: string) => f && f.trim() !== ""))
      .filter((row: string[]) => row.length > 0);
  }

  async function save() {
    if (!metadata) return;
    saving = true;
    cleanFieldLayout();
    try {
      const data = await apiJSON(
        `/api/admin/model-editor/entity/${entityName}`,
        {
          method: "PUT",
          body: JSON.stringify(metadata),
        },
      );
      if (data.status === "success") {
        originalMetadata = JSON.parse(JSON.stringify(metadata));
        hasChanges = false;
        metadataDiff = [];
        showSaveConfirm = false;
      }
    } catch (error) {
      console.error("Failed to save entity:", error);
    } finally {
      saving = false;
    }
  }

  function revertChanges() {
    if (originalMetadata) {
      metadata = JSON.parse(JSON.stringify(originalMetadata));
      hasChanges = false;
      metadataDiff = [];
    }
  }

  function addGridRow(columns: 1 | 2) {
    if (!metadata) return;
    const newRow = columns === 1 ? [""] : ["", ""];
    metadata.field_layout = [...metadata.field_layout, newRow];
    hasChanges = true;
  }

  function removeRow(rowIdx: number) {
    if (!metadata) return;
    metadata.field_layout = metadata.field_layout.filter(
      (_: string[], i: number) => i !== rowIdx,
    );
    hasChanges = true;
  }

  onMount(() => {
    loadEntity();
  });

  // Watch for entity name changes
  $effect(() => {
    if (entityName) {
      loadEntity();
    }
  });
</script>

<div class="flex flex-col gap-6">
  <!-- Header -->
  <div class="flex items-center justify-between">
    <div class="flex items-center gap-3">
      <Button variant="ghost" size="sm" href="/model-editor" class="gap-1.5">
        <ArrowLeftIcon class="size-4" />
        Back
      </Button>
      <h1 class="text-2xl font-bold tracking-tight">
        {metadata?.label || (entityName ? entityName.toUpperCase() : "Entity")}
      </h1>
      {#if metadata}
        <Badge variant="secondary">{metadata.fields.length} fields</Badge>
      {/if}
      {#if !hasChanges}
        <Badge variant="secondary" class="gap-1">
          <CheckIcon class="size-3" />
          In Sync
        </Badge>
      {/if}
    </div>

    <div class="flex items-center gap-2">
      <Button variant="outline" onclick={addField} class="gap-1.5">
        <PlusIcon class="size-4" />
        Add Field
      </Button>
      {#if hasChanges}
        <Button onclick={() => (showSaveConfirm = true)} disabled={saving}>
          <SaveIcon class="size-4" />
          Save
        </Button>
        <Button variant="destructive" onclick={revertChanges} class="gap-1.5">
          <XIcon class="size-4" />
          Cancel
        </Button>
      {/if}
    </div>
  </div>

  <!-- Navigation Tabs -->
  <Tabs.Root bind:value={activeTab} class="w-full">
    <Tabs.List>
      <Tabs.Trigger value="fields">Fields</Tabs.Trigger>
      <Tabs.Trigger value="layout">Layout</Tabs.Trigger>
      <Tabs.Trigger value="relations">Relations</Tabs.Trigger>
      <Tabs.Trigger value="settings">Settings</Tabs.Trigger>
    </Tabs.List>

    <Tabs.Content value="fields">
      <div class="flex flex-col gap-4 md:flex-row">
        <!-- Left: Fields List -->
        <div class="flex-1 overflow-auto">
          {#if metadata}
            <div
              class="flex flex-col gap-2 border rounded-xl p-2"
              use:dndzone={{ items: metadata.fields, flipDurationMs: 150 }}
              onconsider={handleFieldReorder}
              onfinalize={handleFieldReorder}
            >
              {#each metadata.fields as field (field.id)}
                <Item.Root
                  variant="outline"
                  size="sm"
                  class="cursor-move {selectedField?.id === field.id
                    ? 'bg-muted'
                    : ''}"
                  onclick={() =>
                    metadata &&
                    selectField(field, metadata.fields.indexOf(field))}
                >
                  <Item.Media variant="icon">
                    <GripVerticalIcon class="size-4 text-muted-foreground" />
                  </Item.Media>
                  <Item.Content>
                    <Item.Title>{field.label || field.name}</Item.Title>
                  </Item.Content>
                </Item.Root>
              {/each}
            </div>
          {:else}
            <div class="flex items-center justify-center py-12">
              <p class="text-sm text-muted-foreground">
                Loading entity metadata...
              </p>
            </div>
          {/if}
        </div>

        <!-- Right: Field Editor -->
        <div class="w-full overflow-auto border-l p-4 md:w-96">
          {#if selectedField}
            <div class="flex flex-col gap-4">
              <div class="flex items-center justify-between">
                <h3 class="text-lg font-semibold">Field Editor</h3>
                <Button variant="ghost" size="sm" onclick={removeField}>
                  <Trash2Icon class="size-4" />
                </Button>
              </div>

              <!-- Field Details -->
              <div class="flex flex-col gap-3">
                <Field.Field class="gap-1">
                  <Field.Label for="field-label">Label</Field.Label>
                  <Input
                    id="field-label"
                    bind:value={selectedField.label}
                    placeholder="Field Label"
                    oninput={() => (hasChanges = true)}
                  />
                </Field.Field>

                <Field.Field class="gap-1">
                  <Field.Label for="field-name">Field Name</Field.Label>
                  <Input
                    id="field-name"
                    bind:value={selectedField.name}
                    placeholder="field_name"
                    oninput={() => (hasChanges = true)}
                  />
                </Field.Field>

                <Field.Field class="gap-1">
                  <Field.Label for="field-type">Field Type</Field.Label>
                  <Select.Root
                    type="single"
                    value={selectedField.field_type}
                    onValueChange={(v) => {
                      if (selectedField) {
                        selectedField.field_type = v ?? "";
                        hasChanges = true;
                      }
                    }}
                  >
                    <Select.Trigger id="field-type" class="w-full">
                      {FIELD_TYPES.find(
                        (t) => t.value === selectedField!.field_type,
                      )?.label ?? "Select type"}
                    </Select.Trigger>
                    <Select.Content>
                      {#each FIELD_TYPES as type (type.value)}
                        <Select.Item value={type.value} label={type.label}>
                          {type.label}
                        </Select.Item>
                      {/each}
                    </Select.Content>
                  </Select.Root>
                </Field.Field>

                {#if selectedField.field_type === "select"}
                  <Field.Field class="gap-1">
                    <Field.Label for="field-options">
                      Options (one per line)
                    </Field.Label>
                    <Textarea
                      id="field-options"
                      bind:value={selectedField.options}
                      placeholder="Urgent&#10;High&#10;Medium&#10;Low"
                      rows={4}
                      class="font-mono text-sm"
                      oninput={() => {
                        if (
                          selectedField &&
                          typeof selectedField.options === "string"
                        ) {
                          selectedField.options = selectedField.options
                            .split("\n")
                            .filter((o) => o.trim());
                        }
                        hasChanges = true;
                      }}
                    />
                  </Field.Field>
                {/if}

                <Field.Field class="gap-1">
                  <Field.Label for="field-default">Default Value</Field.Label>
                  <Input
                    id="field-default"
                    bind:value={selectedField.default}
                    placeholder="Default value (optional)"
                    oninput={() => (hasChanges = true)}
                  />
                </Field.Field>
              </div>

              <!-- Field Properties -->
              <div class="flex flex-col gap-3 border-t pt-4">
                <h4 class="text-sm font-semibold">Field Properties</h4>
                <div class="flex items-center justify-between">
                  <label for="prop-required" class="text-sm">Required</label>
                  <Switch
                    id="prop-required"
                    bind:checked={selectedField.required}
                    onCheckedChange={() => (hasChanges = true)}
                  />
                </div>
                <div class="flex items-center justify-between">
                  <label for="prop-readonly" class="text-sm">Read Only</label>
                  <Switch
                    id="prop-readonly"
                    bind:checked={selectedField.readonly}
                    onCheckedChange={() => (hasChanges = true)}
                  />
                </div>
                <div class="flex items-center justify-between">
                  <label for="prop-hidden" class="text-sm">Hidden</label>
                  <Switch
                    id="prop-hidden"
                    bind:checked={selectedField.hidden}
                    onCheckedChange={() => (hasChanges = true)}
                  />
                </div>
                <div class="flex items-center justify-between">
                  <label for="prop-listview" class="text-sm">In List View</label
                  >
                  <Switch
                    id="prop-listview"
                    bind:checked={selectedField.in_list_view}
                    onCheckedChange={() => (hasChanges = true)}
                  />
                </div>
                <div class="flex items-center justify-between">
                  <label for="prop-unique" class="text-sm">Unique</label>
                  <Switch
                    id="prop-unique"
                    bind:checked={selectedField.unique}
                    onCheckedChange={() => (hasChanges = true)}
                  />
                </div>
              </div>
            </div>
          {:else}
            <div class="flex flex-col items-center justify-center gap-2 py-12">
              <MousePointerClickIcon class="size-8 text-muted-foreground" />
              <p class="text-sm text-muted-foreground">
                Select a field to edit
              </p>
            </div>
          {/if}
        </div>
      </div>
    </Tabs.Content>

    <Tabs.Content value="layout">
      <div class="flex flex-col gap-4">
        <div class="flex flex-wrap gap-2">
          <Button
            variant="outline"
            size="sm"
            onclick={() => addGridRow(1)}
            class="gap-1.5"
          >
            <PlusIcon class="size-4" />
            1-Column Row
          </Button>
          <Button
            variant="outline"
            size="sm"
            onclick={() => addGridRow(2)}
            class="gap-1.5"
          >
            <PlusIcon class="size-4" />
            2-Column Row
          </Button>
        </div>

        {#if metadata?.field_layout?.length === 0}
          <p class="text-sm text-muted-foreground">
            No layout rows defined. Add a row above and assign fields.
          </p>
        {:else}
          <div class="flex flex-col gap-3">
            {#each metadata?.field_layout ?? [] as row, rowIdx (rowIdx)}
              <div class="rounded-lg border p-3">
                <div class="mb-2 flex items-center justify-between">
                  <span class="text-sm font-medium">
                    Row {rowIdx + 1} · {row.length === 1
                      ? "1 column"
                      : "2 columns"}
                  </span>
                  <Button
                    variant="ghost"
                    size="sm"
                    onclick={() => removeRow(rowIdx)}
                  >
                    <Trash2Icon class="size-4" />
                  </Button>
                </div>
                <div
                  class="grid {row.length === 1
                    ? 'grid-cols-1'
                    : 'grid-cols-2'} gap-3"
                >
                  {#each row as fieldName, colIdx (colIdx)}
                    <Field.Field class="gap-1">
                      <Field.Label>Column {colIdx + 1}</Field.Label>
                      <Select.Root
                        type="single"
                        value={fieldName}
                        onValueChange={(v) => {
                          if (metadata) {
                            metadata.field_layout[rowIdx] = row.map(
                              (f: string, i: number) =>
                                i === colIdx ? (v ?? "") : f,
                            );
                            hasChanges = true;
                          }
                        }}
                      >
                        <Select.Trigger class="w-full">
                          {metadata?.fields?.find((f) => f.name === fieldName)
                            ?.label ||
                            fieldName ||
                            "Select field..."}
                        </Select.Trigger>
                        <Select.Content>
                          <Select.Item value="" label="— None —">
                            — None —
                          </Select.Item>
                          {#each metadata?.fields ?? [] as field (field.name)}
                            <Select.Item
                              value={field.name}
                              label={field.label || field.name}
                            >
                              {field.label || field.name}
                            </Select.Item>
                          {/each}
                        </Select.Content>
                      </Select.Root>
                    </Field.Field>
                  {/each}
                </div>
              </div>
            {/each}
          </div>
        {/if}
      </div>
    </Tabs.Content>

    <Tabs.Content value="relations">
      <div class="flex items-center justify-center py-12">
        <p class="text-sm text-muted-foreground">Relations tab - Coming soon</p>
      </div>
    </Tabs.Content>

    <Tabs.Content value="settings">
      <div class="flex items-center justify-center py-12">
        <p class="text-sm text-muted-foreground">Settings tab - Coming soon</p>
      </div>
    </Tabs.Content>
  </Tabs.Root>
</div>

<!-- Save Confirmation Dialog -->
<Dialog.Root bind:open={showSaveConfirm}>
  <Dialog.Content class="max-w-xl">
    <Dialog.Header>
      <Dialog.Title>Confirm Save</Dialog.Title>
      <Dialog.Description>
        The following changes will be applied to {entityName
          ? entityName.toUpperCase()
          : "this entity"}.
      </Dialog.Description>
    </Dialog.Header>

    <div class="max-h-[60vh] overflow-auto">
      {#if groupedDiff.length}
        <div class="flex flex-col gap-4">
          {#each groupedDiff as group (group.category)}
            <div>
              <div
                class="mb-1.5 flex items-center gap-1 text-sm font-semibold uppercase text-muted-foreground"
              >
                {group.category}
                <Badge variant="secondary">{group.changes.length}</Badge>
              </div>
              <div class="flex flex-col gap-1">
                {#each group.changes as change (change.path)}
                  <div
                    class="flex items-start gap-2 rounded-md border bg-muted p-2 text-sm"
                  >
                    <div class="min-w-0 flex-1">
                      <code class="text-sm text-muted-foreground"
                        >{change.path}</code
                      >
                      <div class="mt-0.5 flex items-center gap-1.5">
                        {#if change.type !== "added"}
                          <span
                            class="truncate text-sm text-destructive line-through"
                          >
                            {formatValue(change.oldValue)}
                          </span>
                        {/if}
                        {#if change.type === "modified"}
                          <span class="shrink-0 text-muted-foreground">→</span>
                        {/if}
                        {#if change.type !== "removed"}
                          <span
                            class="truncate text-sm text-emerald-600 dark:text-emerald-400"
                          >
                            {formatValue(change.newValue)}
                          </span>
                        {/if}
                      </div>
                    </div>
                    <Badge
                      variant={change.type === "added"
                        ? "default"
                        : change.type === "removed"
                          ? "destructive"
                          : "secondary"}
                      class="mt-0.5 shrink-0"
                    >
                      {change.type?.charAt(0).toUpperCase() +
                        change.type?.slice(1)}
                    </Badge>
                  </div>
                {/each}
              </div>
            </div>
          {/each}
        </div>
      {:else}
        <div class="py-4 text-center text-sm text-muted-foreground">
          No changes detected.
        </div>
      {/if}
    </div>

    <Dialog.Footer>
      <Button variant="outline" onclick={() => (showSaveConfirm = false)}>
        Cancel
      </Button>
      <Button onclick={save} disabled={saving} class="gap-1.5">
        <SaveIcon class="size-4" />
        Save
      </Button>
    </Dialog.Footer>
  </Dialog.Content>
</Dialog.Root>
