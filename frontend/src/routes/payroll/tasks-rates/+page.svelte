<script lang="ts">
  import { browser } from "$app/environment";
  import { toast } from "$lib/notifications";
  import { listEntity, saveEntity, deleteEntity } from "$lib/api/index.js";
  import { refCache } from "$lib/task-manager/ref-cache.js";
  import { workspaceApi } from "$lib/workspaces/api.js";
  import type { WorkspaceContext } from "$lib/workspaces/types.js";
  import Button from "$lib/components/design/button.svelte";
  import TextInput from "$lib/components/design/text-input.svelte";
  import Modal from "$lib/components/design/modal.svelte";
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
    const rate = unitRate.trim() === "" ? null : Number(unitRate);
    if (rate === null || Number.isNaN(rate) || rate < 0) {
      toast.error("Enter a valid unit rate");
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
    <Button variant="primary" onclick={openCreate}>
      <PlusIcon size={16} />
      Add task type
    </Button>
  </header>

  <section class="rates-summary" aria-label="Rate catalog summary">
    <div class="summary-card">
      <span class="summary-card__label">Task types</span>
      <strong>{records.length}</strong>
      <span class="summary-card__hint">in the current workspace view</span>
    </div>
    <div class="summary-card">
      <span class="summary-card__label">Workspace rates</span>
      <strong>{records.filter((record) => record.workspace_id).length}</strong>
      <span class="summary-card__hint">assigned to a company</span>
    </div>
    <div class="summary-card">
      <span class="summary-card__label">Approval required</span>
      <strong
        >{records.filter((record) => record.requires_approval).length}</strong
      >
      <span class="summary-card__hint">before payroll eligibility</span>
    </div>
  </section>

  <section class="catalog-panel" aria-labelledby="catalog-title">
    <div class="catalog-toolbar">
      <div>
        <h2 id="catalog-title">Rate catalog</h2>
        <p>Workspace ownership is fixed after a rate is created.</p>
      </div>
      <label class="search-box">
        <SearchIcon size={16} />
        <span class="sr-only">Search task types</span>
        <input bind:value={search} placeholder="Search task types..." />
        {#if search}
          <button
            type="button"
            aria-label="Clear search"
            onclick={() => (search = "")}><XIcon size={15} /></button
          >
        {/if}
      </label>
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
        <span class="empty-icon"><ListChecksIcon size={22} /></span>
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
            <PlusIcon size={15} />
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

<Modal bind:open={modalOpen} labelledBy="task-rate-title" class="rate-modal">
  <form
    class="rate-form"
    onsubmit={(event) => {
      event.preventDefault();
      handleSave();
    }}
  >
    <header class="rate-form__header">
      <div>
        <p class="eyebrow">
          {isEdit ? "Edit catalog item" : "New catalog item"}
        </p>
        <h2 id="task-rate-title">
          {isEdit ? "Edit task type" : "Add a task type"}
        </h2>
        <p>
          {isEdit
            ? "Update the description, rate, and approval rule."
            : "Define who owns this rate and how approved work is paid."}
        </p>
      </div>
      <button
        class="modal-close"
        type="button"
        aria-label="Close dialog"
        onclick={() => (modalOpen = false)}><XIcon size={18} /></button
      >
    </header>

    <div class="rate-form__body">
      {#if canChooseWorkspace || isEdit}
        <label class="form-field">
          <span>Company workspace <b>*</b></span>
          <select
            class="form-control"
            bind:value={workspaceId}
            disabled={isEdit}
            required
          >
            <option value="">Select a workspace</option>
            {#each workspaceContext?.workspaces ?? [] as workspace (workspace.id)}
              <option value={workspace.id}>{workspace.name}</option>
            {/each}
          </select>
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
        <textarea
          id="tt-description"
          class="form-control form-control--area"
          bind:value={description}
          placeholder="A short note to help the team choose the right type"
          rows="3"
          maxlength={1000}></textarea>
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
          <small>Payroll uses this rate for approved work.</small>
        </label>

        <label class="form-field">
          <span>Rate unit <b>*</b></span>
          <select class="form-control" bind:value={unit} required>
            {#each UNIT_OPTIONS as option (option.value)}
              <option value={option.value}>{option.label}</option>
            {/each}
          </select>
        </label>
      </div>

      <label class="approval-setting">
        <input type="checkbox" bind:checked={requiresApproval} />
        <span class="approval-setting__check" aria-hidden="true"></span>
        <span>
          <strong>Require approval</strong>
          <small
            >Work must be approved before it can be included in payroll.</small
          >
        </span>
      </label>
    </div>

    <footer class="rate-form__footer">
      {#if isEdit}
        <Button variant="danger" disabled={saving} onclick={handleDelete}>
          <Trash2Icon size={15} />
          Delete
        </Button>
      {:else}
        <span></span>
      {/if}
      <div class="footer-actions">
        <Button onclick={() => (modalOpen = false)}>Cancel</Button>
        <Button variant="primary" type="submit" disabled={saving}>
          {saving ? "Saving…" : isEdit ? "Save changes" : "Create task type"}
        </Button>
      </div>
    </footer>
  </form>
</Modal>

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
    color: #6d7b91;
    font-size: 10px;
    font-weight: 750;
    letter-spacing: 0.12em;
    text-transform: uppercase;
  }
  .rates-heading h1 {
    margin: 0;
    color: #202a38;
    font-size: clamp(25px, 3vw, 32px);
    font-weight: 700;
    letter-spacing: -0.045em;
  }
  .rates-subtitle {
    margin: 7px 0 0;
    color: #687588;
    font-size: 13px;
  }
  .rates-summary {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 12px;
  }
  .summary-card {
    display: grid;
    min-height: 108px;
    align-content: center;
    gap: 4px;
    border: 1px solid #dbe1e9;
    border-radius: 10px;
    background: #fff;
    padding: 16px 18px;
  }
  .summary-card__label {
    color: #687588;
    font-size: 12px;
    font-weight: 600;
  }
  .summary-card strong {
    color: #202a38;
    font-size: 25px;
    font-weight: 700;
    letter-spacing: -0.04em;
  }
  .summary-card__hint {
    color: #8792a2;
    font-size: 11px;
  }
  .catalog-panel {
    overflow: hidden;
    border: 1px solid #dbe1e9;
    border-radius: 10px;
    background: #fff;
  }
  .catalog-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 18px;
    border-bottom: 1px solid #e7ebf1;
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
    color: #7b8797;
    font-size: 11px;
  }
  .search-box {
    display: flex;
    width: min(280px, 40%);
    min-height: 36px;
    align-items: center;
    gap: 8px;
    border: 1px solid #dbe1e9;
    border-radius: 8px;
    padding: 0 9px;
    color: #7a8798;
  }
  .search-box:focus-within {
    border-color: #7895e8;
    box-shadow: 0 0 0 3px rgb(120 149 232 / 17%);
  }
  .search-box input {
    width: 100%;
    min-width: 0;
    border: 0;
    outline: 0;
    background: transparent;
    color: #202a38;
    font-size: 12px;
  }
  .search-box button {
    display: grid;
    width: 22px;
    height: 22px;
    flex: none;
    place-items: center;
    border: 0;
    background: transparent;
    color: #77869a;
    cursor: pointer;
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
    border-bottom: 1px solid #e7ebf1;
    background: #fafbfd;
    padding: 0 16px;
    color: #758196;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.07em;
    text-transform: uppercase;
  }
  .rates-table td {
    height: 62px;
    border-bottom: 1px solid #edf0f4;
    padding: 8px 16px;
    color: #465469;
    font-size: 12px;
  }
  .rates-table tr:last-child td {
    border-bottom: 0;
  }
  .rates-table tbody tr:hover {
    background: #fafbfd;
  }
  .numeric {
    text-align: right;
  }
  .rate-value {
    color: #26364b !important;
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
    border: 1px solid #dce5f7;
    border-radius: 8px;
    background: #eff3ff;
    color: #2457d6;
    font-size: 12px;
    font-weight: 700;
  }
  .task-name strong,
  .task-name small {
    display: block;
  }
  .task-name strong {
    color: #344256;
    font-size: 12px;
    font-weight: 650;
  }
  .task-name small {
    max-width: 280px;
    overflow: hidden;
    margin-top: 3px;
    color: #8792a2;
    font-size: 10px;
    text-overflow: ellipsis;
  }
  .workspace-badge {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    color: #536176;
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
    border: 1px solid #dbe1e9;
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
    border-color: #cce9da;
    background: #f1faf5;
    color: #28704d;
  }
  .approval-yes > span {
    background: #299465;
  }
  .approval-no {
    background: #f7f8fa;
    color: #687588;
  }
  .approval-no > span {
    background: #9aa5b4;
  }
  .action-cell {
    width: 80px;
    text-align: right;
  }
  .catalog-footer {
    border-top: 1px solid #e7ebf1;
    padding: 11px 17px;
    color: #8792a2;
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
    color: #687588;
    font-size: 13px;
  }
  .loading-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #2457d6;
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
    color: #344256;
    font-size: 14px;
  }
  .catalog-empty p {
    max-width: 350px;
    margin: 0 0 8px;
    color: #7b8797;
    font-size: 12px;
  }
  .empty-icon {
    display: grid;
    width: 45px;
    height: 45px;
    place-items: center;
    border: 1px solid #dbe1e9;
    border-radius: 12px;
    background: #f6f8fb;
    color: #61738e;
  }
  .catalog-error {
    flex-direction: column;
    color: #ad2635;
  }
  .catalog-error span {
    max-width: 600px;
    color: #687588;
  }
  :global(dialog.rate-modal) {
    width: min(580px, calc(100vw - 28px));
  }
  .rate-form__header {
    display: flex;
    justify-content: space-between;
    gap: 14px;
    border-bottom: 1px solid #e7ebf1;
    padding: 22px 24px 18px;
  }
  .rate-form__header h2 {
    margin: 0;
    color: #202a38;
    font-size: 21px;
    font-weight: 700;
  }
  .rate-form__header p:last-child {
    margin: 6px 0 0;
    color: #778396;
    font-size: 12px;
  }
  .modal-close {
    display: grid;
    width: 32px;
    height: 32px;
    flex: none;
    place-items: center;
    border: 1px solid #e0e5ec;
    border-radius: 8px;
    background: #fff;
    color: #687588;
    cursor: pointer;
  }
  .rate-form__body {
    display: flex;
    flex-direction: column;
    gap: 16px;
    padding: 20px 24px;
  }
  .form-field {
    display: flex;
    flex-direction: column;
    gap: 7px;
    color: #465469;
    font-size: 11px;
    font-weight: 650;
  }
  .form-field > span b {
    color: #2457d6;
  }
  .form-field > span small {
    margin-left: 4px;
    color: #8b96a6;
    font-weight: 450;
  }
  .form-field > small {
    color: #8792a2;
    font-size: 10px;
    font-weight: 450;
  }
  .form-control {
    width: 100%;
    min-height: 39px;
    border: 1px solid #cbd3df;
    border-radius: 8px;
    background: #fff;
    padding: 0 11px;
    color: #202a38;
    font-size: 12px;
  }
  .form-control:focus {
    border-color: #2457d6;
    outline: 3px solid rgb(120 149 232 / 20%);
  }
  .form-control:disabled {
    background: #f0f3f7;
    color: #748196;
  }
  .form-control--area {
    min-height: 78px;
    resize: vertical;
    padding: 9px 11px;
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
    color: #687588;
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
    border: 1px solid #dbe1e9;
    border-radius: 9px;
    padding: 12px;
    cursor: pointer;
  }
  .approval-setting input {
    position: absolute;
    width: 1px;
    height: 1px;
    opacity: 0;
  }
  .approval-setting__check {
    display: grid;
    width: 17px;
    height: 17px;
    flex: none;
    place-items: center;
    border: 1px solid #b8c3d2;
    border-radius: 5px;
    background: #fff;
  }
  .approval-setting input:checked + .approval-setting__check {
    border-color: #2457d6;
    background: #2457d6;
  }
  .approval-setting input:checked + .approval-setting__check::after {
    width: 7px;
    height: 4px;
    border-bottom: 2px solid #fff;
    border-left: 2px solid #fff;
    content: "";
    transform: translateY(-1px) rotate(-45deg);
  }
  .approval-setting input:focus-visible + .approval-setting__check {
    outline: 3px solid rgb(120 149 232 / 30%);
  }
  .approval-setting strong,
  .approval-setting small {
    display: block;
  }
  .approval-setting strong {
    color: #344256;
    font-size: 12px;
  }
  .approval-setting small {
    margin-top: 3px;
    color: #8792a2;
    font-size: 10px;
    font-weight: 450;
    line-height: 1.45;
  }
  .rate-form__footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    border-top: 1px solid #e7ebf1;
    background: #fafbfd;
    padding: 13px 24px;
  }
  .footer-actions {
    display: flex;
    gap: 8px;
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
    .rates-summary {
      grid-template-columns: 1fr;
      gap: 8px;
    }
    .summary-card {
      min-height: 82px;
    }
    .catalog-toolbar {
      align-items: stretch;
      flex-direction: column;
    }
    .search-box {
      width: 100%;
    }
    .rate-form__header,
    .rate-form__body,
    .rate-form__footer {
      padding-inline: 16px;
    }
    .form-grid {
      grid-template-columns: 1fr;
    }
    .rate-form__footer {
      align-items: stretch;
      flex-direction: column-reverse;
    }
    .footer-actions {
      justify-content: flex-end;
    }
  }
</style>
