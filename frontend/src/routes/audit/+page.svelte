<script lang="ts">
  import { onMount } from "svelte";
  import { goto } from "$app/navigation";
  import { Button } from "$lib/components/ui/button/index.js";
  import * as Tabs from "$lib/components/ui/tabs/index.js";
  import * as Stats from "$lib/components/ui/stat/index.js";
  import * as Field from "$lib/components/ui/field/index.js";
  import { Input } from "$lib/components/ui/input/index.js";
  import { getToken } from "$lib/auth";
  import { auditApi } from "$lib/audit/api.js";
  import type { AuditLog, Ledger } from "$lib/audit/types.js";
  import { useAppState } from "$lib/app-state.svelte.js";
  import Pagination from "$lib/components/pagination.svelte";

  const appState = useAppState();
  let tab = $state("audit");
  let loading = $state(false);
  let error = $state("");

  let auditFilters = $state({
    reference_entity: "",
    reference_id: "",
    action: "",
    actor_id: "",
    date_from: "",
    date_to: "",
  });
  let auditResult = $state<{
    total: number;
    page: number;
    page_size: number;
    items: AuditLog[];
  }>({ total: 0, page: 1, page_size: 50, items: [] });
  let auditPage = $state(appState.tablePage("audit-logs"));

  let ledgerFilters = $state({
    user_id: "",
    entry_type: "",
    reference_entity: "",
    period_from: "",
    period_to: "",
  });
  let ledgerResult = $state<{
    total: number;
    page: number;
    page_size: number;
    items: Ledger[];
  }>({ total: 0, page: 1, page_size: 50, items: [] });
  let ledgerPage = $state(appState.tablePage("audit-ledger"));

  const ledgerSummary = $derived(() => {
    const items = ledgerResult.items;
    let credits = 0;
    let debits = 0;
    for (const item of items) {
      const amount = Number(item.amount) || 0;
      if (item.entry_type === "credit") credits += amount;
      else if (item.entry_type === "debit") debits += amount;
    }
    return {
      count: items.length,
      credits: Math.round(credits * 100) / 100,
      debits: Math.round(debits * 100) / 100,
      balance: Math.round((credits - debits) * 100) / 100,
    };
  });

  async function loadAudit(page = auditPage) {
    loading = true;
    error = "";
    try {
      const result = await auditApi.getAuditLogs(
        auditFilters,
        page,
        auditResult.page_size,
      );
      if (!result.items.length && result.total > 0 && page > 1) {
        return loadAudit(Math.ceil(result.total / result.page_size));
      }
      auditResult = result;
      auditPage = result.page;
      appState.rememberTablePage("audit-logs", auditPage);
    } catch (err: any) {
      error = err.message || "Failed to load audit logs";
    } finally {
      loading = false;
    }
  }

  async function loadLedger(page = ledgerPage) {
    loading = true;
    error = "";
    try {
      const result = await auditApi.getLedger(
        ledgerFilters,
        page,
        ledgerResult.page_size,
      );
      if (!result.items.length && result.total > 0 && page > 1) {
        return loadLedger(Math.ceil(result.total / result.page_size));
      }
      ledgerResult = result;
      ledgerPage = result.page;
      appState.rememberTablePage("audit-ledger", ledgerPage);
    } catch (err: any) {
      error = err.message || "Failed to load ledger";
    } finally {
      loading = false;
    }
  }

  function setAuditPage(page: number) {
    auditPage = page;
    appState.rememberTablePage("audit-logs", page);
    void loadAudit(page);
  }

  function setLedgerPage(page: number) {
    ledgerPage = page;
    appState.rememberTablePage("audit-ledger", page);
    void loadLedger(page);
  }

  onMount(() => {
    if (!getToken()) {
      void goto("/login");
      return;
    }
    void loadAudit(auditPage);
    void loadLedger(ledgerPage);
  });
</script>

<div class="flex flex-col gap-6">
  <div class="flex flex-wrap items-end justify-between gap-4">
    <h1 class="text-2xl font-bold tracking-tight">Audit & Ledger</h1>
  </div>

  {#if error}
    <p class="rounded-md bg-error/10 p-3 text-sm text-error">
      {error}
    </p>
  {/if}

  <Tabs.Root bind:value={tab}>
    <Tabs.List class="grid w-full max-w-md grid-cols-2">
      <Tabs.Trigger value="audit">Audit Logs</Tabs.Trigger>
      <Tabs.Trigger value="ledger">Ledger</Tabs.Trigger>
    </Tabs.List>

    <Tabs.Content value="audit" class="flex flex-col gap-4 pt-4">
      <div class="grid grid-cols-2 md:grid-cols-5 gap-4">
        <Field.Field class="gap-1">
          <Field.Label for="audit-entity">Entity</Field.Label>
          <Input
            id="audit-entity"
            bind:value={auditFilters.reference_entity}
            placeholder="e.g. task"
          />
        </Field.Field>
        <Field.Field class="gap-1">
          <Field.Label for="audit-ref">Reference ID</Field.Label>
          <Input id="audit-ref" bind:value={auditFilters.reference_id} />
        </Field.Field>
        <Field.Field class="gap-1">
          <Field.Label for="audit-action">Action</Field.Label>
          <Input
            id="audit-action"
            bind:value={auditFilters.action}
            placeholder="e.g. create"
          />
        </Field.Field>
        <Field.Field class="gap-1">
          <Field.Label for="audit-actor">Actor ID</Field.Label>
          <Input id="audit-actor" bind:value={auditFilters.actor_id} />
        </Field.Field>
        <div class="flex items-end">
          <Button onclick={() => setAuditPage(1)} disabled={loading}
            >Search</Button
          >
        </div>
      </div>

      <div class="grid grid-cols-2 gap-4">
        <Field.Field class="gap-1">
          <Field.Label for="audit-from">From</Field.Label>
          <Input
            id="audit-from"
            type="date"
            bind:value={auditFilters.date_from}
          />
        </Field.Field>
        <Field.Field class="gap-1">
          <Field.Label for="audit-to">To</Field.Label>
          <Input id="audit-to" type="date" bind:value={auditFilters.date_to} />
        </Field.Field>
      </div>

      <p class="text-sm text-base-content/60">Total: {auditResult.total}</p>

      <div class="overflow-hidden rounded-box border border-base-300 bg-base-100">
        <table class="table table-zebra">
          <thead>
            <tr>
              <th class="w-[180px]">Timestamp</th>
              <th>Action</th>
              <th>Entity</th>
              <th>Reference ID</th>
              <th>Actor</th>
              <th class="w-[200px]">Old Values</th>
              <th class="w-[200px]">New Values</th>
            </tr>
          </thead>
          <tbody>
            {#each auditResult.items as record (record.id)}
              <tr>
                <td class="text-xs">{record.timestamp}</td>
                <td>{record.action}</td>
                <td>{record.reference_entity}</td>
                <td class="truncate max-w-[120px]"
                  >{record.reference_id}</td
                >
                <td class="truncate max-w-[120px]"
                  >{record.actor_id}</td
                >
                <td>
                  {#if record.old_values}
                    <pre
                      class="text-xs max-w-[200px] overflow-x-auto">{JSON.stringify(
                        record.old_values,
                        null,
                        2,
                      )}</pre>
                  {/if}
                </td>
                <td>
                  {#if record.new_values}
                    <pre
                      class="text-xs max-w-[200px] overflow-x-auto">{JSON.stringify(
                        record.new_values,
                        null,
                        2,
                      )}</pre>
                  {/if}
                </td>
              </tr>
            {:else}
              <tr>
                <td
                  colspan={7}
                  class="text-center text-base-content/60 py-6"
                >
                  No audit logs found
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
        <Pagination
          page={auditPage}
          pageSize={auditResult.page_size}
          total={auditResult.total}
          {loading}
          pageSizeOptions={[25, 50, 100]}
          onchange={setAuditPage}
          onpagesizechange={(size) => {
            auditResult.page_size = size;
            setAuditPage(1);
          }}
        />
      </div>
    </Tabs.Content>

    <Tabs.Content value="ledger" class="flex flex-col gap-4 pt-4">
      <div class="grid grid-cols-2 md:grid-cols-5 gap-4">
        <Field.Field class="gap-1">
          <Field.Label for="ledger-user">User ID</Field.Label>
          <Input id="ledger-user" bind:value={ledgerFilters.user_id} />
        </Field.Field>
        <Field.Field class="gap-1">
          <Field.Label for="ledger-type">Type</Field.Label>
          <Input
            id="ledger-type"
            bind:value={ledgerFilters.entry_type}
            placeholder="credit or debit"
          />
        </Field.Field>
        <Field.Field class="gap-1">
          <Field.Label for="ledger-entity">Entity</Field.Label>
          <Input
            id="ledger-entity"
            bind:value={ledgerFilters.reference_entity}
            placeholder="e.g. payroll_entry"
          />
        </Field.Field>
        <div class="flex items-end">
          <Button onclick={() => setLedgerPage(1)} disabled={loading}
            >Search</Button
          >
        </div>
      </div>

      <div class="grid grid-cols-2 gap-4">
        <Field.Field class="gap-1">
          <Field.Label for="ledger-from">Period From</Field.Label>
          <Input
            id="ledger-from"
            type="date"
            bind:value={ledgerFilters.period_from}
          />
        </Field.Field>
        <Field.Field class="gap-1">
          <Field.Label for="ledger-to">Period To</Field.Label>
          <Input
            id="ledger-to"
            type="date"
            bind:value={ledgerFilters.period_to}
          />
        </Field.Field>
      </div>

      <Stats.Root
        class="w-full stats-vertical border border-base-300 bg-base-100 lg:stats-horizontal"
      >
        <Stats.Item>
          <Stats.Title>Count</Stats.Title>
          <Stats.Value class="tabular-nums">{ledgerSummary().count}</Stats.Value
          >
        </Stats.Item>
        <Stats.Item>
          <Stats.Title>Credits</Stats.Title>
          <Stats.Value class="tabular-nums text-success">
            {ledgerSummary().credits}
          </Stats.Value>
        </Stats.Item>
        <Stats.Item>
          <Stats.Title>Debits</Stats.Title>
          <Stats.Value class="tabular-nums text-error">
            {ledgerSummary().debits}
          </Stats.Value>
        </Stats.Item>
        <Stats.Item>
          <Stats.Title>Balance</Stats.Title>
          <Stats.Value class="tabular-nums"
            >{ledgerSummary().balance}</Stats.Value
          >
        </Stats.Item>
      </Stats.Root>

      <p class="text-sm text-base-content/60">Total: {ledgerResult.total}</p>

      <div class="overflow-hidden rounded-box border border-base-300 bg-base-100">
        <table class="table table-zebra">
          <thead>
            <tr>
              <th class="w-[120px]">Period</th>
              <th>Reference</th>
              <th>User</th>
              <th>Type</th>
              <th class="text-right">Amount</th>
              <th>Description</th>
            </tr>
          </thead>
          <tbody>
            {#each ledgerResult.items as record (record.id)}
              <tr>
                <td class="text-xs">{record.period}</td>
                <td class="truncate max-w-[140px]">
                  {record.reference_entity}:{record.reference_id}
                </td>
                <td class="truncate max-w-[120px]"
                  >{record.user_id}</td
                >
                <td>{record.entry_type}</td>
                <td class="text-right font-mono">
                  {Number(record.amount ?? 0).toFixed(2)}
                </td>
                <td class="truncate max-w-[240px]"
                  >{record.description}</td
                >
              </tr>
            {:else}
              <tr>
                <td
                  colspan={6}
                  class="text-center text-base-content/60 py-6"
                >
                  No ledger entries found
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
        <Pagination
          page={ledgerPage}
          pageSize={ledgerResult.page_size}
          total={ledgerResult.total}
          {loading}
          pageSizeOptions={[25, 50, 100]}
          onchange={setLedgerPage}
          onpagesizechange={(size) => {
            ledgerResult.page_size = size;
            setLedgerPage(1);
          }}
        />
      </div>
    </Tabs.Content>
  </Tabs.Root>
</div>
