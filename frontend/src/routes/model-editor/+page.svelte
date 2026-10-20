<script lang="ts">
  import { onMount } from "svelte";
  import { Button } from "$lib/components/ui/button/index.js";
  import { Input } from "$lib/components/ui/input/index.js";
  import { Badge } from "$lib/components/ui/badge/index.js";
  import * as Table from "$lib/components/ui/table/index.js";
  import { Spinner } from "$lib/components/ui/spinner/index.js";
  import * as Empty from "$lib/components/ui/empty/index.js";
  import RefreshCwIcon from "@lucide/svelte/icons/refresh-cw";
  import GitBranchIcon from "@lucide/svelte/icons/git-branch";
  import SearchIcon from "@lucide/svelte/icons/search";
  import PencilIcon from "@lucide/svelte/icons/pencil";
  import ChevronsUpDownIcon from "@lucide/svelte/icons/chevrons-up-down";
  import CheckIcon from "@lucide/svelte/icons/check";
  import { tick } from "svelte";
  import * as Command from "$lib/components/ui/command/index.js";
  import * as Popover from "$lib/components/ui/popover/index.js";
  import { cn } from "$lib/utils.js";
  import { apiJSON } from "$lib/api/index.js";

  interface ModelEditorEntity {
    name: string;
    label: string;
    module: string;
    field_count: number;
  }

  let entities = $state<ModelEditorEntity[]>([]);
  let loading = $state(true);
  let searchQuery = $state("");
  let selectedModule = $state<string | null>(null);
  let moduleComboboxOpen = $state(false);
  let moduleTriggerRef = $state<HTMLButtonElement>(null!);

  const selectedModuleLabel = $derived(
    selectedModule ? selectedModule.replace(/_/g, " ") : "All Modules",
  );

  function closeAndFocusModuleTrigger() {
    moduleComboboxOpen = false;
    tick().then(() => {
      moduleTriggerRef.focus();
    });
  }

  const modules = $derived.by(() =>
    Array.from(new Set(entities.map((e) => e.module))).sort(),
  );

  const filteredEntities = $derived.by(() => {
    let result = entities;

    if (selectedModule) {
      result = result.filter((e) => e.module === selectedModule);
    }

    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      result = result.filter(
        (e) =>
          e.name.toLowerCase().includes(query) ||
          e.label.toLowerCase().includes(query),
      );
    }

    return result;
  });

  async function loadEntities() {
    loading = true;
    try {
      const data = await apiJSON("/api/admin/model-editor/entities");
      if (data.status === "success") {
        entities = data.data;
      }
    } catch (error) {
      console.error("Failed to load entities:", error);
    } finally {
      loading = false;
    }
  }

  async function reloadMetadata() {
    try {
      const data = await apiJSON("/api/admin/model-editor/reload-metadata", {
        method: "POST",
      });
      if (data.status === "success") {
        await loadEntities();
      }
    } catch (error) {
      console.error("Failed to reload metadata:", error);
    }
  }

  onMount(() => {
    loadEntities();
  });
</script>

<div class="flex flex-col gap-6">
  <!-- Header -->
  <div class="flex items-center justify-between gap-4">
    <div class="flex items-center gap-3">
      <h1 class="text-2xl font-bold tracking-tight">Entity Models</h1>
      <Badge variant="secondary">{filteredEntities.length}</Badge>
    </div>

    <div class="flex items-center gap-3">
      <Button variant="outline" onclick={reloadMetadata} class="gap-1.5">
        <RefreshCwIcon class="size-4" />
        Reload Metadata
      </Button>
      <Button variant="outline" href="/model-editor/migrations" class="gap-1.5">
        <GitBranchIcon class="size-4" />
        Migrations
      </Button>
    </div>
  </div>

  <div class="flex flex-col gap-0">
    <!-- Table Toolbar -->
    <div
      class="flex flex-wrap items-center gap-3 p-2 border border-border rounded-t-xl"
    >
      <div class="relative flex-1 min-w-[150px] max-w-[300px]">
        <SearchIcon
          class="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground"
        />
        <Input
          bind:value={searchQuery}
          placeholder="Search entities..."
          class="pl-9"
        />
      </div>
      <Popover.Root bind:open={moduleComboboxOpen}>
        <Popover.Trigger bind:ref={moduleTriggerRef}>
          {#snippet child({ props })}
            <Button
              {...props}
              variant="outline"
              class="w-48 justify-between"
              role="combobox"
              aria-expanded={moduleComboboxOpen}
            >
              {selectedModuleLabel}
              <ChevronsUpDownIcon class="size-4 opacity-50" />
            </Button>
          {/snippet}
        </Popover.Trigger>
        <Popover.Content class="w-48 p-0">
          <Command.Root>
            <Command.Input placeholder="Search modules..." />
            <Command.List>
              <Command.Empty>No module found.</Command.Empty>
              <Command.Group>
                <Command.Item
                  value=""
                  onSelect={() => {
                    selectedModule = null;
                    closeAndFocusModuleTrigger();
                  }}
                >
                  <CheckIcon
                    class={cn(
                      selectedModule === null ? "opacity-100" : "opacity-0",
                    )}
                  />
                  All Modules
                </Command.Item>
                {#each modules as module (module)}
                  <Command.Item
                    value={module}
                    onSelect={() => {
                      selectedModule = module;
                      closeAndFocusModuleTrigger();
                    }}
                  >
                    <CheckIcon
                      class={cn(
                        selectedModule === module ? "opacity-100" : "opacity-0",
                      )}
                    />
                    {module.replace(/_/g, " ")}
                  </Command.Item>
                {/each}
              </Command.Group>
            </Command.List>
          </Command.Root>
        </Popover.Content>
      </Popover.Root>
      <Button variant="outline" onclick={loadEntities} disabled={loading}>
        <RefreshCwIcon class="size-4 {loading ? 'animate-spin' : ''}" />
      </Button>
    </div>

    <!-- Data Table -->
    <div
      class="flex-1 min-h-0 flex flex-col border-l border-r border-b border-border overflow-auto rounded-b-xl"
    >
      {#if loading}
        <div class="flex items-center justify-center py-12">
          <Spinner class="size-6" />
        </div>
      {:else if filteredEntities.length === 0}
        <Empty.Root class="py-16">
          <Empty.Media variant="icon">
            <PencilIcon />
          </Empty.Media>
          <Empty.Header>
            <Empty.Title>No entities found</Empty.Title>
            <Empty.Description>
              No entities match your current search criteria.
            </Empty.Description>
          </Empty.Header>
        </Empty.Root>
      {:else}
        <Table.Root>
          <Table.Header>
            <Table.Row>
              <Table.Head>Entity</Table.Head>
              <Table.Head>Name</Table.Head>
              <Table.Head>Module</Table.Head>
              <Table.Head>Fields</Table.Head>
              <Table.Head class="text-right">Actions</Table.Head>
            </Table.Row>
          </Table.Header>
          <Table.Body>
            {#each filteredEntities as entity (entity.name)}
              <Table.Row>
                <Table.Cell class="font-medium">{entity.label}</Table.Cell>
                <Table.Cell>
                  <code class="rounded bg-muted px-1.5 py-0.5 text-xs"
                    >{entity.name}</code
                  >
                </Table.Cell>
                <Table.Cell>
                  <Badge variant="secondary">
                    {entity.module.replace(/_/g, " ")}
                  </Badge>
                </Table.Cell>
                <Table.Cell>{entity.field_count}</Table.Cell>
                <Table.Cell class="text-right">
                  <Button
                    variant="ghost"
                    size="sm"
                    href={`/model-editor/${entity.name}`}
                  >
                    <PencilIcon class="size-4" />
                  </Button>
                </Table.Cell>
              </Table.Row>
            {/each}
          </Table.Body>
        </Table.Root>
      {/if}
    </div>
  </div>
</div>
