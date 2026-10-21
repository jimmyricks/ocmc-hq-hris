<script lang="ts">
  import { page } from "$app/state";
  import { browser } from "$app/environment";
  import { goto } from "$app/navigation";
  import { toast } from "$lib/notifications";
  import { payrollApi } from "$lib/payroll/api.js";
  import { taskApi } from "$lib/task-manager/api.js";
  import type {
    PayrollEntry,
    PayrollLineItem,
    PayrollPeriod,
    PayrollSettings,
  } from "$lib/payroll/types.js";
  import type { User } from "$lib/task-manager/types.js";
  import { getToken } from "$lib/auth";
  import { OFFICIAL_CURRENCY } from "$lib/constants.js";

  import * as Card from "$lib/components/ui/card/index.js";
  import * as Empty from "$lib/components/ui/empty/index.js";
  import { Button } from "$lib/components/ui/button/index.js";
  import { Badge } from "$lib/components/ui/badge/index.js";
  import * as Avatar from "$lib/components/ui/avatar/index.js";
  import { Separator } from "$lib/components/ui/separator/index.js";
  import { Skeleton } from "$lib/components/ui/skeleton/index.js";
  import DataTable from "./data-table.svelte";

  import CheckIcon from "@lucide/svelte/icons/check";
  import BanknoteIcon from "@lucide/svelte/icons/banknote";
  import ArrowLeftIcon from "@lucide/svelte/icons/arrow-left";

  let periodId = $derived(page.params.periodId ?? "");
  let entryId = $derived(page.params.entryId ?? "");

  let entry = $state<PayrollEntry | null>(null);
  let period = $state<PayrollPeriod | null>(null);
  let lineItems = $state<PayrollLineItem[]>([]);
  let lineItemTaskInfo = $state<
    Record<
      string,
      {
        taskTitle: string;
        taskKey?: string;
        taskTypeName?: string;
        submissionNotes?: string;
      }
    >
  >({});
  let users = $state<User[]>([]);
  let settings = $state<PayrollSettings>({
    currency: OFFICIAL_CURRENCY,
  } as PayrollSettings);
  let loading = $state(true);
  let error = $state("");

  type LineItemRow = {
    id: string;
    taskTitle: string;
    taskKey?: string;
    taskTypeName?: string;
    submissionNotes?: string;
    rate: string;
    quantity: number;
    amount: string;
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

  // Transform line items + task info into rows for the data table
  let tableData = $derived<LineItemRow[]>(
    lineItems.map((item) => {
      const info = lineItemTaskInfo[item.id];
      return {
        id: item.id,
        taskTitle: info?.taskTitle ?? item.task_submission_id,
        taskKey: info?.taskKey,
        taskTypeName: info?.taskTypeName,
        submissionNotes: info?.submissionNotes,
        rate: formatCurrency(item.rate),
        quantity: item.quantity ?? 1,
        amount: formatCurrency(item.amount),
      };
    }),
  );

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
    loadEntry();
    loadLineItems();
  });

  async function loadEntry() {
    try {
      const entries = await payrollApi.getEntriesForPeriod(periodId);
      entry = entries.find((e) => e.id === entryId) ?? null;
      const periods = await payrollApi.getPeriods();
      period = periods.find((p) => p.id === periodId) ?? null;
    } catch (err: any) {
      error = err.message || "Failed to load entry";
    }
  }

  async function loadLineItems() {
    loading = true;
    try {
      const items = await payrollApi.getLineItemsForEntry(entryId);
      lineItems = items;
      const infoPromises = items.map(async (item) => {
        const info = await payrollApi.getLineItemTaskInfo(
          item.task_submission_id,
        );
        return [item.id, info] as const;
      });
      const infos = await Promise.all(infoPromises);
      lineItemTaskInfo = Object.fromEntries(infos);
    } catch (err: any) {
      toast.error(err.message || "Failed to load line items");
    } finally {
      loading = false;
    }
  }

  async function handleApprove() {
    if (!entry) return;
    try {
      await payrollApi.approveEntry(entry.id);
      toast.success(`Entry approved for ${userName(entry.user_id)}`);
      await loadEntry();
    } catch (err: any) {
      toast.error(err.message || "Failed to approve entry");
    }
  }

  async function handlePay() {
    if (!entry) return;
    if (
      !confirm(
        `Pay ${formatCurrency(entry.total_amount)} to ${userName(entry.user_id)}? This will write a ledger debit and mark the period as paid.`,
      )
    )
      return;
    try {
      await payrollApi.payEntry(entry.id);
      toast.success(`Payment disbursed to ${userName(entry.user_id)}`);
      await loadEntry();
    } catch (err: any) {
      toast.error(err.message || "Failed to pay entry");
    }
  }
</script>

<div class="flex flex-col gap-6">
  <!-- Back link -->
  <Button
    variant="ghost"
    size="sm"
    onclick={() => goto(`/payroll/${periodId}`)}
    class="gap-1.5 text-base-content/60"
  >
    <ArrowLeftIcon class="size-4" />
    Back to {period?.label ?? "period"}
  </Button>

  {#if error}
    <p class="rounded-md bg-error/10 p-3 text-sm text-error">
      {error}
    </p>
  {/if}

  {#if entry}
    {@const es = ENTRY_STATUS_META[entry.status] ?? ENTRY_STATUS_META.draft}

    <!-- Entry header card -->
    <Card.Root>
      <Card.Content class="flex items-center gap-4 pt-6">
        <Avatar.Root class="size-12">
          <Avatar.Fallback class="text-sm"
            >{userInitials(entry.user_id)}</Avatar.Fallback
          >
        </Avatar.Root>
        <div class="flex flex-col gap-1">
          <div class="flex items-center gap-2">
            <h1 class="text-2xl font-bold tracking-tight">
              {userName(entry.user_id)}
            </h1>
            <Badge variant={es.variant}>{es.label}</Badge>
          </div>
          <p class="text-sm text-base-content/60">
            {entry.total_tasks ?? 0}
            {(entry.total_tasks ?? 0) === 1 ? "task" : "tasks"}
            · {formatCurrency(entry.total_amount)}
            {#if entry.approved_at}
              · Approved {formatDate(entry.approved_at)}
            {/if}
          </p>
        </div>
      </Card.Content>
    </Card.Root>

    <!-- Task breakdown data table (below the header card, full width) -->
    <Card.Root>
      <Card.Header>
        <Card.Title>Task Breakdown</Card.Title>
        <Card.Description>
          Approved submissions included in this payroll entry. Each task is
          multiplied by its task type rate.
        </Card.Description>
      </Card.Header>
      <Card.Content>
        {#if loading}
          {#each Array.from({ length: 3 }) as _, i (i)}
            <Skeleton class="h-12 w-full" />
          {/each}
        {:else if lineItems.length === 0}
          <Empty.Root>
            <Empty.Media variant="icon"><BanknoteIcon /></Empty.Media>
            <Empty.Header>
              <Empty.Title>No line items</Empty.Title>
              <Empty.Description
                >This entry has no task submissions.</Empty.Description
              >
            </Empty.Header>
          </Empty.Root>
        {:else}
          <DataTable data={tableData} />
          <Separator class="my-4" />
          <div class="flex items-center justify-between">
            <span class="font-medium">Total</span>
            <span class="text-xl font-bold tabular-nums"
              >{formatCurrency(entry.total_amount)}</span
            >
          </div>
        {/if}
      </Card.Content>
      {#if !loading && lineItems.length > 0}
        <Card.Footer class="flex items-center gap-3">
          {#if entry.status === "draft" || entry.status === "under_review"}
            <Button onclick={handleApprove} class="gap-1.5">
              <CheckIcon class="size-4" />
              Approve Entry
            </Button>
            <p class="text-xs text-base-content/60">
              Approving will verify this entry. All included tasks are already
              closed.
            </p>
          {:else if entry.status === "approved"}
            <Button onclick={handlePay} class="gap-1.5">
              <BanknoteIcon class="size-4" />
              Disburse Payment
            </Button>
            <p class="text-xs text-base-content/60">
              Paying will write a ledger debit and notify the user.
            </p>
          {:else if entry.status === "paid"}
            <div
              class="flex items-center gap-1.5 text-sm text-base-content/60"
            >
              <CheckIcon
                class="size-4 text-success"
              />
              Payment disbursed
              {#if entry.approved_at}
                · Approved {formatDate(entry.approved_at)}
              {/if}
            </div>
          {/if}
        </Card.Footer>
      {/if}
    </Card.Root>
  {:else if loading}
    <Skeleton class="h-20 w-full" />
    <Skeleton class="h-64 w-full" />
  {/if}
</div>
