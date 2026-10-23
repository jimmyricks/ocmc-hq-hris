<script lang="ts">
  import { onMount } from "svelte";
  import { toast } from "$lib/notifications";
  import { saveEntity, deleteEntity } from "$lib/api/index.js";
  import { payrollApi } from "$lib/payroll/api.js";
  import { refCache } from "$lib/task-manager/ref-cache.js";
  import { useAppState } from "$lib/app-state.svelte.js";
  import Pagination from "$lib/components/pagination.svelte";
  import { Button } from "$lib/components/ui/button/index.js";
  import { Checkbox } from "$lib/components/ui/checkbox/index.js";
  import { Input as TextInput } from "$lib/components/ui/input/index.js";
  import * as Select from "$lib/components/ui/select/index.js";
  import * as Stats from "$lib/components/ui/stat/index.js";
  import { Textarea } from "$lib/components/ui/textarea/index.js";
  import * as Dialog from "$lib/components/ui/dialog/index.js";
  import PlusIcon from "@lucide/svelte/icons/plus";
  import PencilIcon from "@lucide/svelte/icons/pencil";
  import Trash2Icon from "@lucide/svelte/icons/trash-2";
  import SearchIcon from "@lucide/svelte/icons/search";
  import XIcon from "@lucide/svelte/icons/x";
  import ListChecksIcon from "@lucide/svelte/icons/list-checks";

  interface TaskType {
    id: string;
    name: string;
    workspace_id?: string | null;
    description?: string | null;
    unit_rate?: number | null;
    unit?: string | null;
    requires_approval?: boolean;
    submission_mode?: string;
  }

  const UNIT_OPTIONS = [
    { value: "per_task", label: "Per task" },
    { value: "per_hour", label: "Per hour" },
    { value: "per_deliverable", label: "Per deliverable" },
    { value: "per_unit", label: "Per unit" },
  ];

  const appState = useAppState();
  let records = $state<TaskType[]>([]);
  const workspaceContext = $derived(appState.workspaceContext);
  let recordsPage = $state(appState.tablePage("task-rates"));
  let recordsPageSize = $state(25);
  let recordsTotal = $state(0);
  let loading = $state(true);
  let error = $state("");
  let search = $state("");
  let appliedSearch = $state("");
  let searchTimer: ReturnType<typeof setTimeout> | undefined;
  let modalOpen = $state(false);
  let isEdit = $state(false);
  let editingId = $state<string | null>(null);
  let saving = $state(false);
  let name = $state("");
  let workspaceId = $state("");
  let description = $state("");
  let unitRate = $state("");
  let unit = $state("per_task");
  let requiresApproval = $state(true);
  let submissionMode = $state("link");

  const canChooseWorkspace = $derived(
    Boolean(workspaceContext?.can_manage && workspaceContext.is_global),
  );
  onMount(() => {
    void appState.ensureBoot();
    void loadData(recordsPage);
    return () => clearTimeout(searchTimer);
  });

  async function loadData(page = recordsPage) {
    loading = true;
    error = "";
    try {
      const result = await payrollApi.getTaskTypesPage(
        page,
        recordsPageSize,
        appliedSearch,
      );
      if (!result.items.length && result.total > 0 && page > 1) {
        return loadData(Math.ceil(result.total / recordsPageSize));
      }
      records = result.items;
      recordsTotal = result.total;
      recordsPage = result.page;
      appState.rememberTablePage("task-rates", recordsPage);
    } catch (err: any) {
      error = err.message || "Failed to load task types";
    } finally {
      loading = false;
    }
  }

  function setRecordsPage(page: number) {
    recordsPage = page;
    appState.rememberTablePage("task-rates", page);
    void loadData(page);
  }

  function queueSearch() {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
      appliedSearch = search.trim();
      setRecordsPage(1);
    }, 300);
  }

  function workspaceName(id: string | null | undefined) {
    if (!id) return "Unassigned";
    return workspaceContext?.workspaces.find((w) => w.id === id)?.name ?? id;
  }

  function workspaceColor(id: string | null | undefined) {
    return workspaceContext?.workspaces.find((w) => w.id === id)?.color;
  }

  function unitLabel(value: string | null | undefined) {
    return (
      UNIT_OPTIONS.find((option) => option.value === value)?.label ??
      value ??
      "—"
    );
  }

  function formatRate(value: number | null | undefined) {
    if (value === null || value === undefined) return "—";
    return `₱${Number(value).toLocaleString(undefined, {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })}`;
  }

  function openCreate() {
    isEdit = false;
    editingId = null;
    name = "";
    workspaceId =
      workspaceContext?.active_workspace_id ??
      workspaceContext?.home_workspace_id ??
      "";
    description = "";
    unitRate = "";
    unit = "per_task";
    requiresApproval = true;
    submissionMode = "link";
    modalOpen = true;
  }

  function openEdit(record: TaskType) {
    isEdit = true;
    editingId = record.id;
    name = record.name ?? "";
    workspaceId = record.workspace_id ?? "";
    description = record.description ?? "";
    unitRate = record.unit_rate != null ? String(record.unit_rate) : "";
    unit = record.unit ?? "per_task";
    requiresApproval = record.requires_approval ?? true;
    submissionMode = record.submission_mode ?? "link";
    modalOpen = true;
  }

  async function handleSave() {
    if (!name.trim()) {
      toast.error("Task type name is required");
      return;
    }
    if ((canChooseWorkspace || isEdit) && !workspaceId) {
      toast.error("Company workspace is required");
      return;
    }
    const rate = unitRate.trim() === "" ? null : Number(unitRate);
    if (rate === null || Number.isNaN(rate) || rate <= 0) {
      toast.error("Enter a positive unit rate");
      return;
    }
    saving = true;
    try {
      const data: Record<string, any> = {
        name: name.trim(),
        description: description.trim() || null,
        unit_rate: rate,
        unit,
        requires_approval: requiresApproval,
        submission_mode: submissionMode,
      };
      if (isEdit && editingId) {
        await saveEntity("task_type", data, editingId);
      } else {
        await saveEntity("task_type", {
          ...data,
          workspace_id: workspaceId || null,
        });
      }
      toast.success(isEdit ? "Task type updated" : "Task type created");
      await loadData(recordsPage);
      refCache.invalidate("task_types");
      modalOpen = false;
    } catch (err: any) {
      toast.error(err.message || "Failed to save task type");
    } finally {
      saving = false;
    }
  }

  async function handleDelete() {
    if (!editingId || !confirm("Delete this task type?")) return;
    saving = true;
    try {
      await deleteEntity("task_type", editingId);
      toast.success("Task type deleted");
      await loadData(recordsPage);
      refCache.invalidate("task_types");
      modalOpen = false;
    } catch (err: any) {
      toast.error(err.message || "Failed to delete task type");
    } finally {
      saving = false;
    }
  }
</script>

<svelte:head>
  <title>Tasks & Rates · OCMC HQ</title>
  <meta
    name="description"
    content="Manage task categories, workspace-specific pay rates, and approval rules."
  />
</svelte:head>

<div class="flex flex-col gap-6">
  <header class="flex flex-wrap items-end justify-between gap-4">
    <div>
      <h1 class="text-2xl font-bold tracking-tight">Tasks &amp; Rates</h1>
      <p class="mt-1 text-sm text-base-content/60">
        Set consistent rates for the work each company delivers.
      </p>
    </div>
    <div class="flex flex-wrap gap-2">
      <a class="btn btn-outline btn-sm" href="/payroll/employee-rates">
        Employee overrides
      </a>
      <Button variant="primary" onclick={openCreate}>
        <PlusIcon size={16} />
        Add task type
      </Button>
    </div>
  </header>

  <Stats.Root
    class="w-full stats-vertical border border-base-300 bg-base-100 lg:stats-horizontal"
    aria-label="Rate catalog summary"
  >
    <Stats.Item>
      <Stats.Title>Task types</Stats.Title>
      <Stats.Value class="tabular-nums">{recordsTotal}</Stats.Value>
      <Stats.Desc>matching task types</Stats.Desc>
    </Stats.Item>
    <Stats.Item>
      <Stats.Title>Workspace rates</Stats.Title>
      <Stats.Value class="tabular-nums"
        >{records.filter((record) => record.workspace_id).length}</Stats.Value
      >
      <Stats.Desc>assigned on this page</Stats.Desc>
    </Stats.Item>
    <Stats.Item>
      <Stats.Title>Approval required</Stats.Title>
      <Stats.Value class="tabular-nums"
        >{records.filter((record) => record.requires_approval)
          .length}</Stats.Value
      >
      <Stats.Desc>on this page</Stats.Desc>
    </Stats.Item>
  </Stats.Root>

  <section
    class="overflow-hidden rounded-box border border-base-300 bg-base-100"
    aria-labelledby="catalog-title"
  >
    <div
      class="flex flex-wrap items-center justify-between gap-3 border-b border-base-300 p-4"
    >
      <div>
        <h2 id="catalog-title" class="font-semibold">Rate catalog</h2>
        <p class="text-sm text-base-content/60">
          Workspace ownership is fixed after a rate is created.
        </p>
      </div>
      <div class="relative w-full sm:w-[min(17.5rem,40%)]">
        <SearchIcon
          size={16}
          class="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-base-content/60"
        />
        <TextInput
          bind:value={search}
          placeholder="Search task types..."
          aria-label="Search task types"
          size="sm"
          class="pl-9 pr-7"
          oninput={queueSearch}
        />
        {#if search}
          <button
            type="button"
            aria-label="Clear search"
            class="absolute right-2 top-1/2 grid size-5 -translate-y-1/2 place-items-center text-base-content/60"
            onclick={() => {
              search = "";
              appliedSearch = "";
              setRecordsPage(1);
            }}><XIcon size={16} /></button
          >
        {/if}
      </div>
    </div>

    {#if error}
      <div class="p-8 text-center" role="alert">
        <p class="font-medium text-error">Could not load rates</p>
        <p class="mt-1 text-sm text-base-content/60">{error}</p>
        <Button size="sm" class="mt-4" onclick={() => loadData(recordsPage)}
          >Try again</Button
        >
      </div>
    {:else if loading}
      <div
        class="flex items-center justify-center gap-2 p-8 text-sm text-base-content/60"
        aria-live="polite"
      >
        <span class="loading loading-spinner loading-sm"></span>
        Loading task rates…
      </div>
    {:else if records.length === 0}
      <div class="p-8 text-center">
        <span
          class="mx-auto mb-3 grid size-11 place-items-center rounded-box border border-base-300 bg-base-200 text-base-content/60"
        >
          <ListChecksIcon size={22} />
        </span>
        <p class="font-medium">
          {search ? "No matching task types" : "No task types yet"}
        </p>
        <p class="mx-auto mt-1 max-w-sm text-sm text-base-content/60">
          {search
            ? "Try another name or workspace."
            : "Add a task type to give your team a clear, consistent rate."}
        </p>
        {#if !search}
          <Button variant="primary" size="sm" class="mt-4" onclick={openCreate}>
            <PlusIcon size={16} />
            Add task type
          </Button>
        {/if}
      </div>
    {:else}
      <div class="overflow-x-auto">
        <table class="table table-zebra">
          <thead>
            <tr>
              <th scope="col">Task type</th>
              <th scope="col">Workspace</th>
              <th scope="col" class="text-right">Rate</th>
              <th scope="col">Rate unit</th>
              <th scope="col">Approval</th>
              <th scope="col"><span class="sr-only">Actions</span></th>
            </tr>
          </thead>
          <tbody>
            {#each records as record (record.id)}
              <tr>
                <td>
                  <button
                    class="flex min-w-0 cursor-pointer items-center gap-2.5 text-left"
                    type="button"
                    onclick={() => openEdit(record)}
                  >
                    <span
                      class="grid size-8 shrink-0 place-items-center rounded-lg bg-primary/10 text-xs font-semibold text-primary"
                    >
                      {record.name.slice(0, 1).toUpperCase()}
                    </span>
                    <span class="min-w-0">
                      <span class="block truncate font-medium"
                        >{record.name}</span
                      >
                      {#if record.description}
                        <span
                          class="block max-w-64 truncate text-xs text-base-content/60"
                          >{record.description}</span
                        >
                      {/if}
                    </span>
                  </button>
                </td>
                <td>
                  <span class="inline-flex items-center gap-1.5">
                    {#if workspaceColor(record.workspace_id)}
                      <span
                        class="size-2 rounded-sm"
                        style:background-color={workspaceColor(
                          record.workspace_id,
                        )}
                      ></span>
                    {/if}
                    {workspaceName(record.workspace_id)}
                  </span>
                </td>
                <td class="text-right font-semibold tabular-nums"
                  >{formatRate(record.unit_rate)}</td
                >
                <td>{unitLabel(record.unit)}</td>
                <td>
                  {#if record.requires_approval}
                    <span class="badge badge-sm badge-success badge-outline"
                      >Required</span
                    >
                  {:else}
                    <span class="badge badge-sm badge-ghost">Not required</span>
                  {/if}
                </td>
                <td class="text-right">
                  <button
                    class="btn btn-ghost btn-sm btn-square"
                    type="button"
                    aria-label="Edit task type"
                    onclick={() => openEdit(record)}
                  >
                    <PencilIcon size={15} />
                  </button>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
      <Pagination
        page={recordsPage}
        pageSize={recordsPageSize}
        total={recordsTotal}
        {loading}
        pageSizeOptions={[10, 25, 50, 100]}
        onchange={setRecordsPage}
        onpagesizechange={(size) => {
          recordsPageSize = size;
          setRecordsPage(1);
        }}
      />
    {/if}
  </section>
</div>

<Dialog.Root bind:open={modalOpen}>
  <Dialog.Content class="relative max-w-xl" aria-labelledby="task-rate-title">
    <form
      onsubmit={(event) => {
        event.preventDefault();
        handleSave();
      }}
    >
      <Dialog.Close
        class="btn btn-ghost btn-sm btn-circle absolute right-2 top-2"
        aria-label="Close dialog"
      >
        <XIcon size={16} />
      </Dialog.Close>
      <Dialog.Header>
        <p class="eyebrow">
          {isEdit ? "Edit catalog item" : "New catalog item"}
        </p>
        <Dialog.Title id="task-rate-title">
          {isEdit ? "Edit task type" : "Add a task type"}
        </Dialog.Title>
        <Dialog.Description>
          {isEdit
            ? "Update the description, rate, and approval rule."
            : "Define who owns this rate and how approved work is paid."}
        </Dialog.Description>
      </Dialog.Header>

      <div class="flex flex-col gap-4">
        {#if canChooseWorkspace || isEdit}
          <label class="form-field">
            <span>Company workspace <b>*</b></span>
            <Select.Root
              type="single"
              bind:value={workspaceId}
              disabled={isEdit}
            >
              <Select.Trigger
                class="w-full"
                aria-label="Company workspace"
                aria-required="true"
              >
                {workspaceId
                  ? workspaceName(workspaceId)
                  : "Select a workspace"}
              </Select.Trigger>
              <Select.Content>
                <Select.Item value="" label="Select a workspace">
                  Select a workspace
                </Select.Item>
                {#each workspaceContext?.workspaces ?? [] as workspace (workspace.id)}
                  <Select.Item value={workspace.id} label={workspace.name}>
                    {workspace.name}
                  </Select.Item>
                {/each}
              </Select.Content>
            </Select.Root>
            {#if isEdit}
              <small
                >Workspace attribution cannot be changed after creation.</small
              >
            {/if}
          </label>
        {/if}

        <label class="form-field">
          <span>Task type name <b>*</b></span>
          <TextInput
            id="tt-name"
            bind:value={name}
            placeholder="e.g. Audio mixing"
            required
            maxlength={255}
          />
        </label>

        <label class="form-field">
          <span>Description <small>Optional</small></span>
          <Textarea
            id="tt-description"
            class="min-h-20 resize-y"
            bind:value={description}
            placeholder="A short note to help the team choose the right type"
            rows={3}
            maxlength={1000}
          />
        </label>

        <div class="form-grid">
          <label class="form-field">
            <span>Unit rate <b>*</b></span>
            <div class="rate-input-wrap">
              <span>₱</span>
              <TextInput
                id="tt-rate"
                type="number"
                min="0"
                step="0.01"
                value={unitRate}
                oninput={(event) => (unitRate = event.currentTarget.value)}
                placeholder="0.00"
                required
              />
            </div>
            <small>
              Payroll pays one approved deliverable. Hourly rates stay
              unavailable until submissions capture hours.
            </small>
          </label>

          <label class="form-field">
            <span>Rate unit <b>*</b></span>
            <Select.Root type="single" bind:value={unit}>
              <Select.Trigger
                class="w-full"
                aria-label="Rate unit"
                aria-required="true"
              >
                {unitLabel(unit)}
              </Select.Trigger>
              <Select.Content>
                {#each UNIT_OPTIONS as option (option.value)}
                  <Select.Item value={option.value} label={option.label}>
                    {option.label}
                  </Select.Item>
                {/each}
              </Select.Content>
            </Select.Root>
          </label>
        </div>

        <label class="form-field">
          <span>Submission format <b>*</b></span>
          <Select.Root type="single" bind:value={submissionMode}>
            <Select.Trigger
              class="w-full"
              aria-label="Submission format"
              aria-required="true"
            >
              {submissionMode === "text" ? "Pasted text" : "External link"}
            </Select.Trigger>
            <Select.Content>
              <Select.Item value="link" label="External link">
                External link
              </Select.Item>
              <Select.Item value="text" label="Pasted text">
                Pasted text
              </Select.Item>
            </Select.Content>
          </Select.Root>
          <small>
            Link tasks (reels, posters) take a URL; text tasks (articles,
            captions) take pasted content at submission.
          </small>
        </label>

        <label class="approval-setting">
          <Checkbox class="mt-0.5" bind:checked={requiresApproval} />
          <span>
            <strong>Require approval</strong>
            <small
              >Work must be approved before it can be included in payroll.</small
            >
          </span>
        </label>
      </div>

      <Dialog.Footer class="justify-between">
        {#if isEdit}
          <Button variant="danger" disabled={saving} onclick={handleDelete}>
            <Trash2Icon size={16} />
            Delete
          </Button>
        {:else}
          <span></span>
        {/if}
        <div class="flex gap-2">
          <Button variant="outline" onclick={() => (modalOpen = false)}>
            Cancel
          </Button>
          <Button variant="primary" type="submit" disabled={saving}>
            {saving ? "Saving…" : isEdit ? "Save changes" : "Create task type"}
          </Button>
        </div>
      </Dialog.Footer>
    </form>
  </Dialog.Content>
</Dialog.Root>

<style>
  .eyebrow {
    margin: 0 0 6px;
    color: color-mix(in oklab, var(--color-base-content) 62%, transparent);
    font-size: 10px;
    font-weight: 750;
    letter-spacing: 0.12em;
    text-transform: uppercase;
  }
  .form-field {
    display: flex;
    flex-direction: column;
    gap: 7px;
    color: var(--color-base-content);
    font-size: 11px;
    font-weight: 650;
  }
  .form-field > span b {
    color: var(--color-primary);
  }
  .form-field > span small {
    margin-left: 4px;
    color: color-mix(in oklab, var(--color-base-content) 62%, transparent);
    font-weight: 450;
  }
  .form-field > small {
    color: color-mix(in oklab, var(--color-base-content) 62%, transparent);
    font-size: 10px;
    font-weight: 450;
  }
  .form-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 14px;
  }
  .rate-input-wrap {
    position: relative;
  }
  .rate-input-wrap > span {
    position: absolute;
    top: 50%;
    left: 11px;
    z-index: 1;
    color: color-mix(in oklab, var(--color-base-content) 62%, transparent);
    font-size: 13px;
    transform: translateY(-50%);
  }
  .rate-input-wrap :global(input) {
    padding-left: 27px;
  }
  .approval-setting {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    border: 1px solid var(--color-base-300);
    border-radius: 9px;
    padding: 12px;
    cursor: pointer;
  }
  .approval-setting strong,
  .approval-setting small {
    display: block;
  }
  .approval-setting strong {
    color: var(--color-base-content);
    font-size: 12px;
  }
  .approval-setting small {
    margin-top: 3px;
    color: color-mix(in oklab, var(--color-base-content) 62%, transparent);
    font-size: 10px;
    font-weight: 450;
    line-height: 1.45;
  }
  @media (max-width: 680px) {
    .form-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
