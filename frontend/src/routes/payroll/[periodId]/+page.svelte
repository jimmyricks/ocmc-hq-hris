<script lang="ts">
  import { page } from "$app/state";
  import { browser } from "$app/environment";
  import { goto } from "$app/navigation";
  import { toast } from "$lib/notifications";
  import { payrollApi } from "$lib/payroll/api.js";
  import { taskApi } from "$lib/task-manager/api.js";
  import type { PayrollEntry, PayrollPeriod } from "$lib/payroll/types.js";
  import type { User } from "$lib/task-manager/types.js";
  import { getToken } from "$lib/auth";
  import { OFFICIAL_CURRENCY } from "$lib/constants.js";

  import * as Card from "$lib/components/ui/card/index.js";
  import * as Empty from "$lib/components/ui/empty/index.js";

  import * as Stats from "$lib/components/ui/stat/index.js";
  import { Button } from "$lib/components/ui/button/index.js";
  import { Badge } from "$lib/components/ui/badge/index.js";
  import * as Avatar from "$lib/components/ui/avatar/index.js";
  import { Skeleton } from "$lib/components/ui/skeleton/index.js";

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
  });

  $effect(() => {
    const currentPeriodId = periodId;
    if (!browser || !getToken() || !currentPeriodId) return;
    period = null;
    entries = [];
    void loadPeriod(currentPeriodId);
    void loadEntries(currentPeriodId);
  });

  async function loadPeriod(currentPeriodId: string) {
    try {
      const result = await payrollApi.getPeriod(currentPeriodId);
      if (page.params.periodId === currentPeriodId) period = result;
    } catch (err: any) {
      if (page.params.periodId === currentPeriodId) {
        error = err.message || "Failed to load period";
      }
    }
  }

  async function loadEntries(currentPeriodId: string) {
    loading = true;
    entriesLoading = true;
    error = "";
    try {
      const result = await payrollApi.getEntriesForPeriod(currentPeriodId);
      if (page.params.periodId === currentPeriodId) entries = result;
    } catch (err: any) {
      if (page.params.periodId === currentPeriodId) {
        error = err.message || "Failed to load payroll entries";
      }
    } finally {
      if (page.params.periodId === currentPeriodId) {
        loading = false;
        entriesLoading = false;
      }
    }
  }

  async function handleGenerate() {
    if (!period) return;
    if (
      !confirm(
        `Generate payroll for "${period.label}"? This includes approved tasks completed during this period.`,
      )
    )
      return;
    try {
      const result = await payrollApi.generate(period.id);
      toast.success(`Generated ${result.count} payroll entries.`);
      await loadEntries(period.id);
      await loadPeriod(period.id);
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
    class="gap-1.5 text-base-content/60"
  >
    <ArrowLeftIcon class="size-4" />
    Back to periods
  </Button>

  {#if error}
    <p class="rounded-md bg-error/10 p-3 text-sm text-error">
      {error}
    </p>
  {/if}

  <!-- Period header + generate button -->
  {#if period}
    <div class="flex flex-wrap items-end justify-between gap-4">
      <div>
        <div class="flex items-center gap-2">
          <h1 class="text-2xl font-bold tracking-tight">{period.label}</h1>
          <Badge variant={PERIOD_STATUS_META[period.status]?.variant}>
            {PERIOD_STATUS_META[period.status]?.label}
          </Badge>
        </div>
        <p class="mt-1 text-sm text-base-content/60">
          Done date window: {formatDate(period.start_date)} →
          {formatDate(period.end_date)} (inclusive)
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
    <Stats.Root
      class="w-full stats-vertical border border-base-300 bg-base-100 lg:stats-horizontal"
    >
      <Stats.Item>
        <Stats.Figure class="text-primary"
          ><UsersIcon class="size-6" /></Stats.Figure
        >
        <Stats.Title>Users</Stats.Title>
        <Stats.Value class="tabular-nums">{entries.length}</Stats.Value>
      </Stats.Item>
      <Stats.Item>
        <Stats.Figure class="text-primary"
          ><ListTodoIcon class="size-6" /></Stats.Figure
        >
        <Stats.Title>Total Tasks</Stats.Title>
        <Stats.Value class="tabular-nums">{periodTaskCount()}</Stats.Value>
      </Stats.Item>
      <Stats.Item>
        <Stats.Figure class="text-primary"
          ><DollarSignIcon class="size-6" /></Stats.Figure
        >
        <Stats.Title>Period Total</Stats.Title>
        <Stats.Value class="tabular-nums"
          >{formatCurrency(periodTotal())}</Stats.Value
        >
      </Stats.Item>
    </Stats.Root>
  {:else if loading}
    <Skeleton class="h-16 w-full" />
  {/if}

  <!-- Per-user entries list -->
  {#if entriesLoading}
    <ul class="list w-full rounded-box bg-base-100 shadow-md">
      {#each Array.from({ length: 3 }) as _, i (i)}
        <li class="list-row items-center">
          <div><Skeleton class="size-10 rounded-xl" /></div>
          <div>
            <Skeleton class="h-4 w-32" />
            <Skeleton class="mt-1 h-3 w-20" />
          </div>
          <Skeleton class="h-6 w-16" />
        </li>
      {/each}
    </ul>
  {:else if entries.length === 0}
    <Card.Root>
      <Card.Content class="pt-6">
        <Empty.Root>
          <Empty.Media variant="icon"><BanknoteIcon /></Empty.Media>
          <Empty.Header>
            <Empty.Title>No payroll entries</Empty.Title>
            <Empty.Description>
              Generate payroll to include approved tasks moved to Done during
              this cutoff.
            </Empty.Description>
          </Empty.Header>
        </Empty.Root>
      </Card.Content>
    </Card.Root>
  {:else}
    <ul class="list w-full rounded-box bg-base-100 shadow-md">
      {#each entries as entry (entry.id)}
        {@const es = ENTRY_STATUS_META[entry.status] ?? ENTRY_STATUS_META.draft}
        <li>
          <a
            class="list-row items-center"
            href={`/payroll/${periodId}/${entry.id}`}
          >
            <div>
              <Avatar.Root class="size-10">
                <Avatar.Fallback class="text-xs"
                  >{userInitials(entry.user_id)}</Avatar.Fallback
                >
              </Avatar.Root>
            </div>
            <div>
              <div class="font-medium">{userName(entry.user_id)}</div>
              <div class="text-xs opacity-60">
                {entry.total_tasks ?? 0}
                {(entry.total_tasks ?? 0) === 1 ? "task" : "tasks"}
              </div>
            </div>
            <div class="flex items-center gap-2">
              <span class="text-lg font-bold tabular-nums"
                >{formatCurrency(entry.total_amount)}</span
              >
              <Badge variant={es.variant}>{es.label}</Badge>
              <ChevronRightIcon class="size-4 text-base-content/60" />
            </div>
          </a>
        </li>
      {/each}
    </ul>
  {/if}
</div>
