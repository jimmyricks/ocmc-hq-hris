<script lang="ts">
  import { browser } from "$app/environment";
  import { toast } from "$lib/notifications";
  import { listEntity, saveEntity, deleteEntity } from "$lib/api/index.js";
  import { refCache } from "$lib/task-manager/ref-cache.js";
  import { workspaceApi } from "$lib/workspaces/api.js";
  import type { WorkspaceContext } from "$lib/workspaces/types.js";
  import { Button } from "$lib/components/ui/button/index.js";
  import { Checkbox } from "$lib/components/ui/checkbox/index.js";
  import { Input as TextInput } from "$lib/components/ui/input/index.js";
  import * as Select from "$lib/components/ui/select/index.js";
  import * as Stats from "$lib/components/ui/stat/index.js";
  import { Textarea } from "$lib/components/ui/textarea/index.js";
  import * as Dialog from "$lib/components/ui/dialog/index.js";
  import PlusIcon from "@lucide/svelte/icons/plus";
  import Trash2Icon from "@lucide/svelte/icons/trash-2";
  import SearchIcon from "@lucide/svelte/icons/search";
  import XIcon from "@lucide/svelte/icons/x";
  import ListChecksIcon from "@lucide/svelte/icons/list-checks";

  interface TaskType {
    id: string;
    name: string;
    workspace_id: string | null;
    description: string | null;
    unit_rate: number | null;
    unit: string | null;
    requires_approval: boolean;
  }

  const UNIT_OPTIONS = [
    { value: "per_task", label: "Per task" },
    { value: "per_hour", label: "Per hour" },
    { value: "per_deliverable", label: "Per deliverable" },
    { value: "per_unit", label: "Per unit" },
  ];

  let records = $state<TaskType[]>([]);
  let workspaceContext = $state<WorkspaceContext | null>(null);
  let loading = $state(true);
  let error = $state("");
  let search = $state("");
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

  const canChooseWorkspace = $derived(
    Boolean(workspaceContext?.can_manage && workspaceContext.is_global),
  );
  const filteredRecords = $derived(
    records.filter((record) =>
      `${record.name} ${workspaceName(record.workspace_id)}`
        .toLowerCase()
        .includes(search.trim().toLowerCase()),
    ),
  );

  $effect(() => {
    if (!browser) return;
    loadData();
    workspaceApi
      .getContext()
      .then((ctx) => (workspaceContext = ctx))
      .catch((err) => console.error("Failed to load workspace context:", err));
  });

  async function loadData() {
    loading = true;
    error = "";
    try {
      const res = await listEntity("task_type", 1, 100);
      records = (res.data ?? []) as TaskType[];
    } catch (err: any) {
      error = err.message || "Failed to load task types";
    } finally {
      loading = false;
    }
  }

  function workspaceName(id: string | null) {
    if (!id) return "Unassigned";
    return workspaceContext?.workspaces.find((w) => w.id === id)?.name ?? id;
  }

  function workspaceColor(id: string | null) {
    return workspaceContext?.workspaces.find((w) => w.id === id)?.color;
  }

  function unitLabel(value: string | null) {
    return (
      UNIT_OPTIONS.find((option) => option.value === value)?.label ??
      value ??
      "—"
    );
  }

  function formatRate(value: number | null) {
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
      await loadData();
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
      await loadData();
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

<div class="rates-page">
  <header class="rates-heading">
    <div>
      <p class="eyebrow">Payroll setup</p>
      <h1>Tasks &amp; Rates</h1>
      <p class="rates-subtitle">
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
      <Stats.Value class="tabular-nums">{records.length}</Stats.Value>
      <Stats.Desc>in the current workspace view</Stats.Desc>
    </Stats.Item>
    <Stats.Item>
      <Stats.Title>Workspace rates</Stats.Title>
      <Stats.Value class="tabular-nums"
        >{records.filter((record) => record.workspace_id).length}</Stats.Value
      >
      <Stats.Desc>assigned to a company</Stats.Desc>
    </Stats.Item>
    <Stats.Item>
      <Stats.Title>Approval required</Stats.Title>
      <Stats.Value class="tabular-nums"
        >{records.filter((record) => record.requires_approval)
          .length}</Stats.Value
      >
      <Stats.Desc>before payroll eligibility</Stats.Desc>
    </Stats.Item>
  </Stats.Root>

  <section class="catalog-panel" aria-labelledby="catalog-title">
    <div class="catalog-toolbar">
      <div>
        <h2 id="catalog-title">Rate catalog</h2>
        <p>Workspace ownership is fixed after a rate is created.</p>
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
        />
        {#if search}
          <button
            type="button"
            aria-label="Clear search"
            class="absolute right-2 top-1/2 grid size-5 -translate-y-1/2 place-items-center text-base-content/60"
            onclick={() => (search = "")}><XIcon size={16} /></button
          >
        {/if}
      </div>
    </div>

    {#if error}
      <div class="catalog-error" role="alert">
        <strong>Could not load rates</strong>
        <span>{error}</span>
        <Button size="sm" onclick={loadData}>Try again</Button>
      </div>
    {:else if loading}
      <div class="catalog-loading" aria-live="polite">
        <span class="loading-dot"></span>
        Loading task rates…
      </div>
    {:else if filteredRecords.length === 0}
      <div class="catalog-empty">
        <span class="empty-icon"><ListChecksIcon size={24} /></span>
        <strong
          >{search ? "No matching task types" : "No task types yet"}</strong
        >
        <p>
          {search
            ? "Try another name or workspace."
            : "Add a task type to give your team a clear, consistent rate."}
        </p>
        {#if !search}
          <Button variant="primary" size="sm" onclick={openCreate}>
            <PlusIcon size={16} />
            Add task type
          </Button>
        {/if}
      </div>
    {:else}
      <div class="rates-table-wrap">
        <table class="rates-table">
          <thead>
            <tr>
              <th scope="col">Task type</th>
              <th scope="col">Workspace</th>
              <th scope="col" class="numeric">Rate</th>
              <th scope="col">Rate unit</th>
              <th scope="col">Approval</th>
              <th scope="col"><span class="sr-only">Actions</span></th>
            </tr>
          </thead>
          <tbody>
            {#each filteredRecords as record (record.id)}
              <tr>
                <td>
                  <button
                    class="task-name"
                    type="button"
                    onclick={() => openEdit(record)}
                  >
                    <span class="task-name__mark"
                      >{record.name.slice(0, 1).toUpperCase()}</span
                    >
                    <span>
                      <strong>{record.name}</strong>
                      {#if record.description}
                        <small>{record.description}</small>
                      {/if}
                    </span>
                  </button>
                </td>
                <td>
                  <span class="workspace-badge">
                    {#if workspaceColor(record.workspace_id)}
                      <span
                        class="workspace-badge__dot"
                        style:background-color={workspaceColor(
                          record.workspace_id,
                        )}
                      ></span>
                    {/if}
                    {workspaceName(record.workspace_id)}
                  </span>
                </td>
                <td class="numeric rate-value"
                  >{formatRate(record.unit_rate)}</td
                >
                <td>{unitLabel(record.unit)}</td>
                <td>
                  <span
                    class:approval-yes={record.requires_approval}
                    class:approval-no={!record.requires_approval}
                    class="approval-pill"
                  >
                    <span></span>
                    {record.requires_approval ? "Required" : "Not required"}
                  </span>
                </td>
                <td class="action-cell">
                  <Button size="sm" onclick={() => openEdit(record)}
                    >Edit</Button
                  >
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
      <div class="catalog-footer">
        Showing {filteredRecords.length} of {records.length} task types
      </div>
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
                bind:value={unitRate}
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
  .rates-page {
    display: flex;
    flex-direction: column;
    gap: 22px;
  }
  .rates-heading {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 20px;
  }
  .eyebrow {
    margin: 0 0 6px;
    color: color-mix(in oklab, var(--color-base-content) 62%, transparent);
    font-size: 10px;
    font-weight: 750;
    letter-spacing: 0.12em;
    text-transform: uppercase;
  }
  .rates-heading h1 {
    margin: 0;
    color: var(--color-base-content);
    font-size: clamp(25px, 3vw, 32px);
    font-weight: 700;
    letter-spacing: -0.045em;
  }
  .rates-subtitle {
    margin: 7px 0 0;
    color: color-mix(in oklab, var(--color-base-content) 62%, transparent);
    font-size: 13px;
  }
  .catalog-panel {
    overflow: hidden;
    border: 1px solid var(--color-base-300);
    border-radius: 10px;
    background: var(--color-base-100);
  }
  .catalog-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 18px;
    border-bottom: 1px solid var(--color-base-300);
    padding: 17px 19px;
  }
  .catalog-toolbar h2 {
    margin: 0;
    font-size: 15px;
    font-weight: 700;
    letter-spacing: -0.02em;
  }
  .catalog-toolbar p {
    margin: 4px 0 0;
    color: color-mix(in oklab, var(--color-base-content) 62%, transparent);
    font-size: 11px;
  }

  .rates-table-wrap {
    overflow-x: auto;
  }
  .rates-table {
    width: 100%;
    border-collapse: collapse;
    text-align: left;
    white-space: nowrap;
  }
  .rates-table th {
    height: 41px;
    border-bottom: 1px solid var(--color-base-300);
    background: var(--color-base-200);
    padding: 0 16px;
    color: color-mix(in oklab, var(--color-base-content) 62%, transparent);
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.07em;
    text-transform: uppercase;
  }
  .rates-table td {
    height: 62px;
    border-bottom: 1px solid var(--color-base-300);
    padding: 8px 16px;
    color: var(--color-base-content);
    font-size: 12px;
  }
  .rates-table tr:last-child td {
    border-bottom: 0;
  }
  .rates-table tbody tr:hover {
    background: var(--color-base-200);
  }
  .numeric {
    text-align: right;
  }
  .rate-value {
    color: var(--color-base-content) !important;
    font-variant-numeric: tabular-nums;
    font-weight: 700;
  }
  .task-name {
    display: flex;
    align-items: center;
    gap: 10px;
    border: 0;
    background: transparent;
    padding: 0;
    color: inherit;
    text-align: left;
    cursor: pointer;
  }
  .task-name__mark {
    display: grid;
    width: 32px;
    height: 32px;
    flex: none;
    place-items: center;
    border: 1px solid
      color-mix(in oklab, var(--color-primary) 12%, var(--color-base-100));
    border-radius: 8px;
    background: color-mix(
      in oklab,
      var(--color-primary) 12%,
      var(--color-base-100)
    );
    color: var(--color-primary);
    font-size: 12px;
    font-weight: 700;
  }
  .task-name strong,
  .task-name small {
    display: block;
  }
  .task-name strong {
    color: var(--color-base-content);
    font-size: 12px;
    font-weight: 650;
  }
  .task-name small {
    max-width: 280px;
    overflow: hidden;
    margin-top: 3px;
    color: color-mix(in oklab, var(--color-base-content) 62%, transparent);
    font-size: 10px;
    text-overflow: ellipsis;
  }
  .workspace-badge {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    color: var(--color-base-content);
  }
  .workspace-badge__dot {
    width: 8px;
    height: 8px;
    border-radius: 3px;
  }
  .approval-pill {
    display: inline-flex;
    min-height: 24px;
    align-items: center;
    gap: 6px;
    border: 1px solid var(--color-base-300);
    border-radius: 999px;
    padding: 0 8px;
    font-size: 10px;
    font-weight: 650;
  }
  .approval-pill > span {
    width: 6px;
    height: 6px;
    border-radius: 50%;
  }
  .approval-yes {
    border-color: color-mix(
      in oklab,
      var(--color-success) 22%,
      var(--color-base-100)
    );
    background: color-mix(
      in oklab,
      var(--color-success) 8%,
      var(--color-base-100)
    );
    color: var(--color-success);
  }
  .approval-yes > span {
    background: var(--color-success);
  }
  .approval-no {
    background: var(--color-base-200);
    color: color-mix(in oklab, var(--color-base-content) 62%, transparent);
  }
  .approval-no > span {
    background: color-mix(in oklab, var(--color-base-content) 62%, transparent);
  }
  .action-cell {
    width: 80px;
    text-align: right;
  }
  .catalog-footer {
    border-top: 1px solid var(--color-base-300);
    padding: 11px 17px;
    color: color-mix(in oklab, var(--color-base-content) 62%, transparent);
    font-size: 10px;
  }
  .catalog-loading,
  .catalog-empty,
  .catalog-error {
    display: flex;
    min-height: 205px;
    align-items: center;
    justify-content: center;
    gap: 10px;
    color: color-mix(in oklab, var(--color-base-content) 62%, transparent);
    font-size: 13px;
  }
  .loading-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--color-primary);
    animation: pulse 1s ease-in-out infinite alternate;
  }
  .catalog-empty {
    flex-direction: column;
    gap: 6px;
    padding: 25px;
    text-align: center;
  }
  .catalog-empty strong {
    margin-top: 5px;
    color: var(--color-base-content);
    font-size: 14px;
  }
  .catalog-empty p {
    max-width: 350px;
    margin: 0 0 8px;
    color: color-mix(in oklab, var(--color-base-content) 62%, transparent);
    font-size: 12px;
  }
  .empty-icon {
    display: grid;
    width: 45px;
    height: 45px;
    place-items: center;
    border: 1px solid var(--color-base-300);
    border-radius: 12px;
    background: var(--color-base-200);
    color: color-mix(in oklab, var(--color-base-content) 62%, transparent);
  }
  .catalog-error {
    flex-direction: column;
    color: var(--color-error);
  }
  .catalog-error span {
    max-width: 600px;
    color: color-mix(in oklab, var(--color-base-content) 62%, transparent);
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
  @keyframes pulse {
    to {
      opacity: 0.35;
      transform: scale(0.75);
    }
  }
  @media (max-width: 680px) {
    .rates-heading {
      align-items: flex-start;
      flex-direction: column;
    }
    .catalog-toolbar {
      align-items: stretch;
      flex-direction: column;
    }
    .form-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
