<script lang="ts">
  import { goto } from "$app/navigation";
  import { Button } from "$lib/components/ui/button/index.js";
  import * as Tabs from "$lib/components/ui/tabs/index.js";
  import * as Table from "$lib/components/ui/table/index.js";
  import * as Stats from "$lib/components/ui/stat/index.js";
  import * as Field from "$lib/components/ui/field/index.js";
  import { Input } from "$lib/components/ui/input/index.js";
  import { getToken } from "$lib/auth";
  import { auditApi } from "$lib/audit/api.js";
  import type { AuditLog, Ledger } from "$lib/audit/types.js";

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
  let auditResult = $state<{ total: number; items: AuditLog[] }>({
    total: 0,
    items: [],
  });

  let ledgerFilters = $state({
    user_id: "",
    entry_type: "",
    reference_entity: "",
    period_from: "",
    period_to: "",
  });
  let ledgerResult = $state<{ total: number; items: Ledger[] }>({
    total: 0,
    items: [],
  });

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

  async function loadAudit() {
    loading = true;
    error = "";
    try {
      auditResult = await auditApi.getAuditLogs(auditFilters, 1, 50);
    } catch (err: any) {
      error = err.message || "Failed to load audit logs";
    } finally {
      loading = false;
    }
  }

  async function loadLedger() {
    loading = true;
    error = "";
    try {
      ledgerResult = await auditApi.getLedger(ledgerFilters, 1, 50);
    } catch (err: any) {
      error = err.message || "Failed to load ledger";
    } finally {
      loading = false;
    }
  }

  $effect(() => {
    if (!getToken()) {
      goto("/login");
      return;
    }
    loadAudit();
    loadLedger();
  });
</script>

<div class="flex flex-col gap-6">
  <div class="flex items-center justify-between">
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
          <Button onclick={loadAudit} disabled={loading}>Search</Button>
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

      <div class="border rounded-xl overflow-hidden">
        <Table.Root>
          <Table.Header class="bg-base-200/100">
            <Table.Row>
              <Table.Head class="w-[180px]">Timestamp</Table.Head>
              <Table.Head>Action</Table.Head>
              <Table.Head>Entity</Table.Head>
              <Table.Head>Reference ID</Table.Head>
              <Table.Head>Actor</Table.Head>
              <Table.Head class="w-[200px]">Old Values</Table.Head>
              <Table.Head class="w-[200px]">New Values</Table.Head>
            </Table.Row>
          </Table.Header>
          <Table.Body>
            {#each auditResult.items as record (record.id)}
              <Table.Row>
                <Table.Cell class="text-xs">{record.timestamp}</Table.Cell>
                <Table.Cell>{record.action}</Table.Cell>
                <Table.Cell>{record.reference_entity}</Table.Cell>
                <Table.Cell class="truncate max-w-[120px]"
                  >{record.reference_id}</Table.Cell
                >
                <Table.Cell class="truncate max-w-[120px]"
                  >{record.actor_id}</Table.Cell
                >
                <Table.Cell>
                  {#if record.old_values}
                    <pre
                      class="text-xs max-w-[200px] overflow-x-auto">{JSON.stringify(
                        record.old_values,
                        null,
                        2,
                      )}</pre>
                  {/if}
                </Table.Cell>
                <Table.Cell>
                  {#if record.new_values}
                    <pre
                      class="text-xs max-w-[200px] overflow-x-auto">{JSON.stringify(
                        record.new_values,
                        null,
                        2,
                      )}</pre>
                  {/if}
                </Table.Cell>
              </Table.Row>
            {:else}
              <Table.Row>
                <Table.Cell
                  colspan={7}
                  class="text-center text-base-content/60 py-6"
                >
                  No audit logs found
                </Table.Cell>
              </Table.Row>
            {/each}
          </Table.Body>
        </Table.Root>
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
          <Button onclick={loadLedger} disabled={loading}>Search</Button>
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
          <Stats.Value class="tabular-nums">{ledgerSummary().count}</Stats.Value>
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
          <Stats.Value class="tabular-nums">{ledgerSummary().balance}</Stats.Value>
        </Stats.Item>
      </Stats.Root>

      <p class="text-sm text-base-content/60">Total: {ledgerResult.total}</p>

      <div class="border rounded-xl overflow-hidden">
        <Table.Root>
          <Table.Header class="bg-base-200/100">
            <Table.Row>
              <Table.Head class="w-[120px]">Period</Table.Head>
              <Table.Head>Reference</Table.Head>
              <Table.Head>User</Table.Head>
              <Table.Head>Type</Table.Head>
              <Table.Head class="text-right">Amount</Table.Head>
              <Table.Head>Description</Table.Head>
            </Table.Row>
          </Table.Header>
          <Table.Body>
            {#each ledgerResult.items as record (record.id)}
              <Table.Row>
                <Table.Cell class="text-xs">{record.period}</Table.Cell>
                <Table.Cell class="truncate max-w-[140px]">
                  {record.reference_entity}:{record.reference_id}
                </Table.Cell>
                <Table.Cell class="truncate max-w-[120px]"
                  >{record.user_id}</Table.Cell
                >
                <Table.Cell>{record.entry_type}</Table.Cell>
                <Table.Cell class="text-right font-mono">
                  {Number(record.amount ?? 0).toFixed(2)}
                </Table.Cell>
                <Table.Cell class="truncate max-w-[240px]"
                  >{record.description}</Table.Cell
                >
              </Table.Row>
            {:else}
              <Table.Row>
                <Table.Cell
                  colspan={6}
                  class="text-center text-base-content/60 py-6"
                >
                  No ledger entries found
                </Table.Cell>
              </Table.Row>
            {/each}
          </Table.Body>
        </Table.Root>
      </div>
    </Tabs.Content>
  </Tabs.Root>
</div>
