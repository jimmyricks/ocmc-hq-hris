<script lang="ts">
  import { page } from "$app/state";
  import { browser } from "$app/environment";
  import { goto } from "$app/navigation";
  import { toast } from "$lib/notifications";
  import { payrollApi } from "$lib/payroll/api.js";
  import { taskApi } from "$lib/task-manager/api.js";
  import type {
    PayrollEntry,
    PayrollPeriod,
    PayrollSettings,
  } from "$lib/payroll/types.js";
  import type { User } from "$lib/task-manager/types.js";
  import { getToken } from "$lib/auth";
  import { OFFICIAL_CURRENCY } from "$lib/constants.js";

  import * as Card from "$lib/components/native/card/index.js";
  import * as Empty from "$lib/components/native/empty/index.js";
  import * as Item from "$lib/components/native/item/index.js";
  import { Button } from "$lib/components/native/button/index.js";
  import { Badge } from "$lib/components/native/badge/index.js";
  import * as Avatar from "$lib/components/native/avatar/index.js";
  import { Skeleton } from "$lib/components/native/skeleton/index.js";

  import PlayIcon from "@lucide/svelte/icons/play";
  import BanknoteIcon from "@lucide/svelte/icons/banknote";
  import ChevronRightIcon from "@lucide/svelte/icons/chevron-right";
  import ArrowLeftIcon from "@lucide/svelte/icons/arrow-left";
  import UsersIcon from "@lucide/svelte/icons/users";
  import ListTodoIcon from "@lucide/svelte/icons/list-todo";
  import DollarSignIcon from "@lucide/svelte/icons/dollar-sign";

  let periodId = $derived(page.params.periodId ?? "");
  let period = $state<PayrollPeriod | null>(null);
  let entries = $state<PayrollEntry[]>([]);
  let users = $state<User[]>([]);
  let settings = $state<PayrollSettings>({
    currency: OFFICIAL_CURRENCY,
  } as PayrollSettings);
  let loading = $state(true);
  let entriesLoading = $state(true);
  let error = $state("");

  const PERIOD_STATUS_META: Record<
    string,
    { label: string; variant: "outline" | "secondary" | "default" }
  > = {
    open: { label: "Open", variant: "outline" },
    closed: { label: "Closed", variant: "secondary" },
    paid: { label: "Paid", variant: "default" },
  };

  const ENTRY_STATUS_META: Record<
    string,
    { label: string; variant: "outline" | "secondary" | "default" }
  > = {
    draft: { label: "Draft", variant: "outline" },
    under_review: { label: "Under Review", variant: "secondary" },
    approved: { label: "Approved", variant: "default" },
    paid: { label: "Paid", variant: "default" },
  };

  function formatCurrency(value: number | string | undefined): string {
    const n = Number(value ?? 0);
    return new Intl.NumberFormat("en-PH", {
      style: "currency",
      currency: OFFICIAL_CURRENCY,
    }).format(n);
  }

  function formatDate(d?: string): string {
    if (!d) return "—";
    return d.split("T")[0];
  }

  function userName(id: string): string {
    return users.find((u) => u.id === id)?.full_name ?? id;
  }

  function userInitials(id: string): string {
    return userName(id)
      .split(" ")
      .map((p) => p[0])
      .filter(Boolean)
      .slice(0, 2)
      .join("")
      .toUpperCase();
  }

  function periodTotal(): number {
    return entries.reduce((sum, e) => sum + (Number(e.total_amount) || 0), 0);
  }

  function periodTaskCount(): number {
    return entries.reduce((sum, e) => sum + (Number(e.total_tasks) || 0), 0);
  }

  $effect(() => {
    if (!browser) return;
    if (!getToken()) {
      goto("/login");
      return;
    }
    taskApi
      .getUsers()
      .then((u) => (users = u))
      .catch(() => {});
    payrollApi
      .getSettings()
      .then((s) => {
        if (s) settings = s;
      })
      .catch(() => {});
    loadPeriod();
    loadEntries();
  });

  async function loadPeriod() {
    try {
      const periods = await payrollApi.getPeriods();
      period = periods.find((p) => p.id === periodId) ?? null;
    } catch (err: any) {
      error = err.message || "Failed to load period";
    }
  }

  async function loadEntries() {
    loading = true;
    entriesLoading = true;
    error = "";
    try {
      entries = await payrollApi.getEntriesForPeriod(periodId);
    } catch (err: any) {
      error = err.message || "Failed to load payroll entries";
    } finally {
      loading = false;
      entriesLoading = false;
    }
  }

  async function handleGenerate() {
    if (!period) return;
    if (
      !confirm(
        `Generate payroll for "${period.label}"? This will auto-close all approved tasks in the period.`,
      )
    )
      return;
    try {
      const result = await payrollApi.generate(period.id);
      toast.success(
        `Generated ${result.count} payroll entries. Approved tasks have been closed.`,
      );
      await loadEntries();
      await loadPeriod();
    } catch (err: any) {
      toast.error(err.message || "Failed to generate payroll");
    }
  }
</script>

<div class="flex flex-col gap-6">
  <!-- Back link -->
  <Button
    variant="ghost"
    size="sm"
    onclick={() => goto("/payroll")}
    class="gap-1.5 text-muted-foreground"
  >
    <ArrowLeftIcon class="size-4" />
    Back to periods
  </Button>

  {#if error}
    <p class="rounded-md bg-destructive/10 p-3 text-sm text-destructive">
      {error}
    </p>
  {/if}

  <!-- Period header + generate button -->
  {#if period}
    <div
      class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between"
    >
      <div>
        <div class="flex items-center gap-2">
          <h1 class="text-2xl font-bold tracking-tight">{period.label}</h1>
          <Badge variant={PERIOD_STATUS_META[period.status]?.variant}>
            {PERIOD_STATUS_META[period.status]?.label}
          </Badge>
        </div>
        <p class="text-sm text-muted-foreground">
          {formatDate(period.start_date)} → {formatDate(period.end_date)}
          {#if period.cutoff && period.cutoff !== period.end_date}
            · Cutoff: {formatDate(period.cutoff)}
          {/if}
        </p>
      </div>
      <Button
        variant="outline"
        onclick={handleGenerate}
        class="gap-1.5"
        disabled={period.status === "paid"}
      >
        <PlayIcon class="size-4" />
        {entries.length > 0 ? "Regenerate" : "Generate Payroll"}
      </Button>
    </div>

    <!-- Summary stats -->
    <Item.Group class="grid grid-cols-3 gap-4">
      <Item.Root variant="outline">
        <Item.Media variant="icon"><UsersIcon /></Item.Media>
        <Item.Content>
          <Item.Description>Users</Item.Description>
          <Item.Title class="text-2xl font-bold tabular-nums"
            >{entries.length}</Item.Title
          >
        </Item.Content>
      </Item.Root>
      <Item.Root variant="outline">
        <Item.Media variant="icon"><ListTodoIcon /></Item.Media>
        <Item.Content>
          <Item.Description>Total Tasks</Item.Description>
          <Item.Title class="text-2xl font-bold tabular-nums"
            >{periodTaskCount()}</Item.Title
          >
        </Item.Content>
      </Item.Root>
      <Item.Root variant="outline">
        <Item.Media variant="icon"><DollarSignIcon /></Item.Media>
        <Item.Content>
          <Item.Description>Period Total</Item.Description>
          <Item.Title class="text-2xl font-bold tabular-nums"
            >{formatCurrency(periodTotal())}</Item.Title
          >
        </Item.Content>
      </Item.Root>
    </Item.Group>
  {:else if loading}
    <Skeleton class="h-16 w-full" />
  {/if}

  <!-- Per-user entries list -->
  {#if entriesLoading}
    <Item.Group>
      {#each Array.from({ length: 3 }) as _, i (i)}
        <Item.Root variant="outline">
          <Item.Media variant="image"
            ><Skeleton class="size-10 rounded-xl" /></Item.Media
          >
          <Item.Content>
            <Item.Title><Skeleton class="h-4 w-32" /></Item.Title>
            <Item.Description><Skeleton class="h-3 w-20" /></Item.Description>
          </Item.Content>
          <Item.Actions><Skeleton class="h-6 w-16" /></Item.Actions>
        </Item.Root>
      {/each}
    </Item.Group>
  {:else if entries.length === 0}
    <Card.Root>
      <Card.Content class="pt-6">
        <Empty.Root>
          <Empty.Media variant="icon"><BanknoteIcon /></Empty.Media>
          <Empty.Header>
            <Empty.Title>No payroll entries</Empty.Title>
            <Empty.Description>
              Click "Generate Payroll" to scan approved submissions and create
              entries per user.
            </Empty.Description>
          </Empty.Header>
        </Empty.Root>
      </Card.Content>
    </Card.Root>
  {:else}
    <Item.Group>
      {#each entries as entry (entry.id)}
        {@const es = ENTRY_STATUS_META[entry.status] ?? ENTRY_STATUS_META.draft}
        <Item.Root variant="outline">
          {#snippet child({ props })}
            <a href={`/payroll/${periodId}/${entry.id}`} {...props}>
              <Item.Media variant="image">
                <Avatar.Root class="size-full">
                  <Avatar.Fallback class="text-xs"
                    >{userInitials(entry.user_id)}</Avatar.Fallback
                  >
                </Avatar.Root>
              </Item.Media>
              <Item.Content>
                <Item.Title>{userName(entry.user_id)}</Item.Title>
                <Item.Description>
                  {entry.total_tasks ?? 0}
                  {(entry.total_tasks ?? 0) === 1 ? "task" : "tasks"}
                </Item.Description>
              </Item.Content>
              <Item.Actions>
                <span class="text-lg font-bold tabular-nums"
                  >{formatCurrency(entry.total_amount)}</span
                >
                <Badge variant={es.variant}>{es.label}</Badge>
                <ChevronRightIcon class="size-4 text-muted-foreground" />
              </Item.Actions>
            </a>
          {/snippet}
        </Item.Root>
      {/each}
    </Item.Group>
  {/if}
</div>
