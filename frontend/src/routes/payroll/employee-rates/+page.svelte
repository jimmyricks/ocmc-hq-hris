<script lang="ts">
  import { onMount } from "svelte";
  import { payrollApi } from "$lib/payroll/api.js";
  import type {
    EmployeeRateOptions,
    UserTaskRate,
  } from "$lib/payroll/types.js";
  import { Button } from "$lib/components/ui/button/index.js";
  import { Input } from "$lib/components/ui/input/index.js";
  import { useAppState } from "$lib/app-state.svelte.js";
  import Pagination from "$lib/components/pagination.svelte";
  import PlusIcon from "@lucide/svelte/icons/plus";
  import Trash2Icon from "@lucide/svelte/icons/trash-2";
  import PencilIcon from "@lucide/svelte/icons/pencil";

  const appState = useAppState();
  let rates = $state<UserTaskRate[]>([]);
  let ratesPage = $state(appState.tablePage("employee-rates"));
  let ratesPageSize = $state(25);
  let ratesTotal = $state(0);
  let options = $state<EmployeeRateOptions>({
    workspaces: [],
    users: [],
    task_types: [],
  });
  let summary = $state<{
    period_count: number;
    entry_count: number;
    approved_submission_count: number;
    payroll_total: number;
    invoice_total: number;
  } | null>(null);
  let loading = $state(true);
  let saving = $state(false);
  let error = $state("");
  let filter = $state("");
  let appliedFilter = $state("");
  let filterTimer: ReturnType<typeof setTimeout> | undefined;
  let editorOpen = $state(false);
  let editingId = $state<string | null>(null);
  let workspaceId = $state("");
  let userId = $state("");
  let taskTypeId = $state("");
  let rateValue = $state("");

  const availableUsers = $derived(
    options.users.filter((user) => user.workspace_ids.includes(workspaceId)),
  );
  const availableTaskTypes = $derived(
    options.task_types.filter(
      (taskType) => taskType.workspace_id === workspaceId,
    ),
  );

  onMount(() => {
    void loadRates(ratesPage);
    void loadReferenceData();
    return () => clearTimeout(filterTimer);
  });

  async function loadReferenceData() {
    try {
      const [choices, payrollSummary] = await Promise.all([
        payrollApi.getEmployeeRateOptions(),
        payrollApi.getHrSummary(),
      ]);
      options = choices;
      summary = payrollSummary;
    } catch (err) {
      error =
        err instanceof Error ? err.message : "Could not load rate options";
    }
  }

  async function loadRates(page = ratesPage) {
    loading = true;
    error = "";
    try {
      const result = await payrollApi.getEmployeeRatesPage(
        page,
        ratesPageSize,
        appliedFilter,
      );
      if (!result.items.length && result.total > 0 && page > 1) {
        return loadRates(Math.ceil(result.total / ratesPageSize));
      }
      rates = result.items;
      ratesTotal = result.total;
      ratesPage = result.page;
      appState.rememberTablePage("employee-rates", ratesPage);
    } catch (err) {
      error =
        err instanceof Error ? err.message : "Could not load employee rates";
    } finally {
      loading = false;
    }
  }

  function setRatesPage(page: number) {
    ratesPage = page;
    appState.rememberTablePage("employee-rates", page);
    void loadRates(page);
  }

  function queueSearch() {
    clearTimeout(filterTimer);
    filterTimer = setTimeout(() => {
      appliedFilter = filter.trim();
      setRatesPage(1);
    }, 300);
  }

  function workspaceName(id: string) {
    return (
      options.workspaces.find((workspace) => workspace.id === id)?.name ?? id
    );
  }

  function userName(id: string) {
    const user = options.users.find((item) => item.id === id);
    return user ? `${user.full_name} (${user.email})` : id;
  }

  function taskTypeName(id: string) {
    return options.task_types.find((item) => item.id === id)?.name ?? id;
  }

  function openCreate() {
    editingId = null;
    workspaceId = options.workspaces[0]?.id ?? "";
    userId = "";
    taskTypeId = "";
    rateValue = "";
    editorOpen = true;
  }

  function openEdit(record: UserTaskRate) {
    editingId = record.id;
    workspaceId = record.workspace_id;
    userId = record.user_id;
    taskTypeId = record.task_type_id;
    rateValue = String(record.rate);
    editorOpen = true;
  }

  async function save() {
    const amount = Number(rateValue);
    if (
      !workspaceId ||
      !userId ||
      !taskTypeId ||
      !Number.isFinite(amount) ||
      amount <= 0
    ) {
      error = "Choose an employee, workspace, task type, and positive rate.";
      return;
    }
    if (Math.round(amount * 100) !== amount * 100) {
      error = "Rates can have at most two decimal places.";
      return;
    }
    saving = true;
    error = "";
    try {
      await payrollApi.saveEmployeeRate(
        {
          workspace_id: workspaceId,
          user_id: userId,
          task_type_id: taskTypeId,
          rate: amount,
        },
        editingId ?? undefined,
      );
      editorOpen = false;
      await loadRates(ratesPage);
    } catch (err) {
      error =
        err instanceof Error ? err.message : "Could not save employee rate";
    } finally {
      saving = false;
    }
  }

  async function remove(record: UserTaskRate) {
    if (
      !confirm(
        `Remove ${taskTypeName(record.task_type_id)} override for ${userName(record.user_id)}?`,
      )
    ) {
      return;
    }
    try {
      await payrollApi.deleteEmployeeRate(record.id);
      await loadRates(ratesPage);
    } catch (err) {
      error =
        err instanceof Error ? err.message : "Could not delete employee rate";
    }
  }
</script>

<svelte:head>
  <title>Employee Rates · OCMC HQ</title>
  <meta
    name="description"
    content="Manage workspace-specific employee pay overrides and review global payroll totals."
  />
</svelte:head>

<main class="mx-auto flex w-full max-w-7xl flex-col gap-6 p-4 md:p-8">
  <header class="flex flex-wrap items-end justify-between gap-4">
    <div>
      <p
        class="text-xs font-semibold uppercase tracking-[0.14em] text-base-content/60"
      >
        Payroll setup
      </p>
      <h1 class="mt-2 text-2xl font-bold tracking-tight">
        Employee rate overrides
      </h1>
      <p class="mt-1 max-w-2xl text-sm text-base-content/60">
        Overrides apply to one employee, task type, and workspace. Approved
        submissions keep the exact rate and amount captured at approval.
      </p>
    </div>
    <div class="flex gap-2">
      <a class="btn btn-outline btn-sm" href="/payroll/tasks-rates"
        >Task type defaults</a
      >
      <Button variant="primary" onclick={openCreate}>
        <PlusIcon size={16} />
        Add override
      </Button>
    </div>
  </header>

  {#if error}
    <div class="alert alert-error" role="alert">
      <span>{error}</span>
      <button
        class="btn btn-ghost btn-xs"
        type="button"
        onclick={() => (error = "")}>Dismiss</button
      >
    </div>
  {/if}

  {#if summary}
    <section
      class="stats stats-vertical w-full border border-base-300 bg-base-100 shadow-sm sm:stats-horizontal"
      aria-label="Global payroll summary"
    >
      <div class="stat">
        <div class="stat-title">Payroll periods</div>
        <div class="stat-value text-2xl">{summary.period_count}</div>
      </div>
      <div class="stat">
        <div class="stat-title">Payroll entries</div>
        <div class="stat-value text-2xl">{summary.entry_count}</div>
      </div>
      <div class="stat">
        <div class="stat-title">Approved submissions</div>
        <div class="stat-value text-2xl">
          {summary.approved_submission_count}
        </div>
      </div>
      <div class="stat">
        <div class="stat-title">Payroll / invoices</div>
        <div class="stat-value text-xl">
          ₱{Number(summary.payroll_total).toLocaleString(undefined, {
            minimumFractionDigits: 2,
          })}
        </div>
        <div class="stat-desc">
          Invoice total ₱{Number(summary.invoice_total).toLocaleString(
            undefined,
            { minimumFractionDigits: 2 },
          )}
        </div>
      </div>
    </section>
  {/if}

  <section
    class="overflow-hidden rounded-box border border-base-300 bg-base-100"
  >
    <div
      class="flex flex-wrap items-center justify-between gap-3 border-b border-base-300 p-4"
    >
      <div>
        <h2 class="font-semibold">Rate breakdown</h2>
        <p class="text-sm text-base-content/60">
          Unique by employee x task type x workspace.
        </p>
      </div>
      <Input
        bind:value={filter}
        class="w-full sm:max-w-xs"
        placeholder="Search employees, tasks, workspaces"
        aria-label="Search employee rates"
        oninput={queueSearch}
      />
    </div>

    {#if loading}
      <div
        class="p-8 text-center text-sm text-base-content/60"
        aria-live="polite"
      >
        Loading payroll rates…
      </div>
    {:else if rates.length === 0}
      <div class="p-8 text-center">
        <p class="font-medium">No employee overrides found</p>
        <p class="mt-1 text-sm text-base-content/60">
          Employees use their workspace task-type default until an override is
          added.
        </p>
      </div>
    {:else}
      <div class="overflow-x-auto">
        <table class="table table-zebra">
          <thead>
            <tr>
              <th>Employee</th>
              <th>Workspace</th>
              <th>Task type</th>
              <th class="text-right">Override</th>
              <th><span class="sr-only">Actions</span></th>
            </tr>
          </thead>
          <tbody>
            {#each rates as record (record.id)}
              <tr>
                <td class="font-medium">{userName(record.user_id)}</td>
                <td>{workspaceName(record.workspace_id)}</td>
                <td>{taskTypeName(record.task_type_id)}</td>
                <td class="text-right font-semibold tabular-nums">
                  ₱{Number(record.rate).toLocaleString(undefined, {
                    minimumFractionDigits: 2,
                  })}
                </td>
                <td class="text-right">
                  <div class="join">
                    <button
                      class="btn btn-ghost btn-sm join-item"
                      type="button"
                      aria-label="Edit rate"
                      onclick={() => openEdit(record)}
                    >
                      <PencilIcon size={15} />
                    </button>
                    <button
                      class="btn btn-ghost btn-sm text-error join-item"
                      type="button"
                      aria-label="Delete rate"
                      onclick={() => remove(record)}
                    >
                      <Trash2Icon size={15} />
                    </button>
                  </div>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
      <Pagination
        page={ratesPage}
        pageSize={ratesPageSize}
        total={ratesTotal}
        {loading}
        pageSizeOptions={[10, 25, 50, 100]}
        onchange={setRatesPage}
        onpagesizechange={(size) => {
          ratesPageSize = size;
          setRatesPage(1);
        }}
      />
    {/if}
  </section>
</main>

{#if editorOpen}
  <div class="modal modal-open" role="presentation">
    <button
      class="modal-backdrop"
      aria-label="Close rate editor"
      onclick={() => (editorOpen = false)}
    ></button>
    <dialog
      open
      class="modal-box max-w-xl"
      aria-labelledby="employee-rate-title"
    >
      <h2 id="employee-rate-title" class="text-xl font-bold">
        {editingId ? "Edit employee override" : "Add employee override"}
      </h2>
      <p class="mb-5 mt-1 text-sm text-base-content/60">
        Changing this rate affects future approvals only.
      </p>
      <form
        class="flex flex-col gap-4"
        onsubmit={(event) => {
          event.preventDefault();
          save();
        }}
      >
        <label class="form-control gap-1">
          <span class="label-text font-medium">Workspace</span>
          <select
            class="select select-bordered"
            bind:value={workspaceId}
            onchange={() => {
              userId = "";
              taskTypeId = "";
            }}
            required
          >
            <option value="" disabled>Select workspace</option>
            {#each options.workspaces as workspace (workspace.id)}
              <option value={workspace.id}>{workspace.name}</option>
            {/each}
          </select>
        </label>
        <label class="form-control gap-1">
          <span class="label-text font-medium">Employee</span>
          <select class="select select-bordered" bind:value={userId} required>
            <option value="" disabled>Select employee</option>
            {#each availableUsers as employee (employee.id)}
              <option value={employee.id}
                >{employee.full_name} - {employee.email}</option
              >
            {/each}
          </select>
        </label>
        <label class="form-control gap-1">
          <span class="label-text font-medium">Task type</span>
          <select
            class="select select-bordered"
            bind:value={taskTypeId}
            required
          >
            <option value="" disabled>Select task type</option>
            {#each availableTaskTypes as taskType (taskType.id)}
              <option value={taskType.id}>{taskType.name}</option>
            {/each}
          </select>
        </label>
        <label class="form-control gap-1">
          <span class="label-text font-medium">Override rate (PHP)</span>
          <Input
            type="number"
            min="0.01"
            step="0.01"
            bind:value={rateValue}
            placeholder="0.00"
            required
          />
        </label>
        <div class="modal-action">
          <button
            class="btn btn-ghost"
            type="button"
            onclick={() => (editorOpen = false)}>Cancel</button
          >
          <Button variant="primary" disabled={saving}>
            {saving ? "Saving…" : editingId ? "Save changes" : "Add override"}
          </Button>
        </div>
      </form>
    </dialog>
  </div>
{/if}
