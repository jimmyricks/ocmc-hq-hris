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
  } from "$lib/payroll/types.js";
  import type { User } from "$lib/task-manager/types.js";
  import { getToken } from "$lib/auth";
  import { useAppState } from "$lib/app-state.svelte.js";
  import Pagination from "$lib/components/pagination.svelte";
  import { OFFICIAL_CURRENCY } from "$lib/constants.js";

  import * as Card from "$lib/components/ui/card/index.js";
  import * as Empty from "$lib/components/ui/empty/index.js";
  import { Button } from "$lib/components/ui/button/index.js";
  import { Badge } from "$lib/components/ui/badge/index.js";
  import * as Avatar from "$lib/components/ui/avatar/index.js";
  import { Skeleton } from "$lib/components/ui/skeleton/index.js";
  import DataTable from "./data-table.svelte";

  import CheckIcon from "@lucide/svelte/icons/check";
  import BanknoteIcon from "@lucide/svelte/icons/banknote";
  import ArrowLeftIcon from "@lucide/svelte/icons/arrow-left";

  let periodId = $derived(page.params.periodId ?? "");
  let entryId = $derived(page.params.entryId ?? "");
  const appState = useAppState();

  let entry = $state<PayrollEntry | null>(null);
  let period = $state<PayrollPeriod | null>(null);
  let lineItems = $state<PayrollLineItem[]>([]);
  let lineItemsPage = $state(1);
  let lineItemsPageSize = $state(25);
  let lineItemsTotal = $state(0);
  let lineItemTaskInfo = $state<
    Record<
      string,
      {
        taskTitle: string;
        taskTypeName?: string;
        submissionNotes?: string;
      }
    >
  >({});
  let users = $state<User[]>([]);
  let loading = $state(true);
  let error = $state("");
  let loadedRouteKey = $state("");

  type LineItemRow = {
    id: string;
    taskTitle: string;
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
        taskTitle: info?.taskTitle ?? "Task details unavailable",
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
  });

  $effect(() => {
    const currentPeriodId = periodId;
    const currentEntryId = entryId;
    const routeKey = `${currentPeriodId}:${currentEntryId}`;
    if (
      !browser ||
      !getToken() ||
      !currentPeriodId ||
      !currentEntryId ||
      loadedRouteKey === routeKey
    ) {
      return;
    }
    loadedRouteKey = routeKey;
    entry = null;
    period = null;
    lineItems = [];
    lineItemTaskInfo = {};
    error = "";
    const storedPage = appState.tablePage("payroll-line-items", currentEntryId);
    lineItemsPage = storedPage;
    loading = true;
    void loadRoute(currentPeriodId, currentEntryId, storedPage, routeKey);
  });

  async function loadRoute(
    currentPeriodId: string,
    currentEntryId: string,
    targetPage: number,
    routeKey: string,
  ) {
    try {
      const [loadedEntry, loadedPeriod] = await Promise.all([
        payrollApi.getEntryForPeriod(currentPeriodId, currentEntryId),
        payrollApi.getPeriod(currentPeriodId),
      ]);
      if (`${page.params.periodId}:${page.params.entryId}` !== routeKey) return;
      entry = loadedEntry;
      period = loadedPeriod;
      await loadLineItems(targetPage, currentEntryId, routeKey);
    } catch (err: any) {
      if (`${page.params.periodId}:${page.params.entryId}` === routeKey) {
        error = err.message || "Failed to load entry";
      }
    } finally {
      if (`${page.params.periodId}:${page.params.entryId}` === routeKey) {
        loading = false;
      }
    }
  }

  async function loadLineItems(
    targetPage = lineItemsPage,
    currentEntryId = entryId,
    routeKey = `${periodId}:${entryId}`,
  ) {
    loading = true;
    try {
      const result = await payrollApi.getLineItemsForEntryPage(
        currentEntryId,
        targetPage,
        lineItemsPageSize,
      );
      if (!result.items.length && result.total > 0 && targetPage > 1) {
        return await loadLineItems(
          Math.ceil(result.total / lineItemsPageSize),
          currentEntryId,
          routeKey,
        );
      }
      if (`${page.params.periodId}:${page.params.entryId}` !== routeKey) return;
      lineItems = result.items;
      lineItemsTotal = result.total;
      lineItemsPage = result.page;
      appState.rememberTablePage(
        "payroll-line-items",
        lineItemsPage,
        currentEntryId,
      );
      const infoPromises = lineItems.map(async (item) => {
        const info = await payrollApi.getLineItemTaskInfo(
          item.task_submission_id,
        );
        return [item.id, info] as const;
      });
      const infos = await Promise.all(infoPromises);
      if (`${page.params.periodId}:${page.params.entryId}` === routeKey) {
        lineItemTaskInfo = Object.fromEntries(infos);
      }
    } catch (err: any) {
      if (`${page.params.periodId}:${page.params.entryId}` === routeKey) {
        toast.error(err.message || "Failed to load line items");
      }
    } finally {
      if (`${page.params.periodId}:${page.params.entryId}` === routeKey) {
        loading = false;
      }
    }
  }

  function setLineItemsPage(targetPage: number) {
    lineItemsPage = targetPage;
    appState.rememberTablePage("payroll-line-items", targetPage, entryId);
    void loadLineItems(targetPage);
  }

  async function handleApprove() {
    if (!entry) return;
    try {
      await payrollApi.approveEntry(entry.id);
      toast.success(
        `Entry approved and invoice issued for ${userName(entry.user_id)}`,
      );
      await loadRoute(
        periodId,
        entryId,
        lineItemsPage,
        `${periodId}:${entryId}`,
      );
    } catch (err: any) {
      toast.error(err.message || "Failed to approve entry");
    }
  }

  async function handlePay() {
    if (!entry) return;
    if (
      !confirm(
        `Pay ${formatCurrency(entry.total_amount)} to ${userName(entry.user_id)}? This will write a ledger debit and mark this entry as paid.`,
      )
    )
      return;
    try {
      await payrollApi.payEntry(entry.id);
      toast.success(`Payment disbursed to ${userName(entry.user_id)}`);
      await loadRoute(
        periodId,
        entryId,
        lineItemsPage,
        `${periodId}:${entryId}`,
      );
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

    <Card.Root>
      <Card.Header
        class="flex-col items-start justify-between gap-4 sm:flex-row sm:items-center"
      >
        <div>
          <Card.Title>Workflow</Card.Title>
          <Card.Description>
            Review this payroll entry and take its next available action.
          </Card.Description>
        </div>
        <Card.Action class="w-full sm:w-auto">
          {#if entry.status === "draft" || entry.status === "under_review"}
            <Button
              onclick={handleApprove}
              disabled={loading || lineItems.length === 0}
              class="gap-1.5"
            >
              <CheckIcon class="size-4" />
              Approve Entry
            </Button>
          {:else if entry.status === "approved"}
            <Button
              onclick={handlePay}
              disabled={loading || lineItems.length === 0}
              class="gap-1.5"
            >
              <BanknoteIcon class="size-4" />
              Disburse Payment
            </Button>
          {:else if entry.status === "paid"}
            <Badge variant="default" class="gap-1.5">
              <CheckIcon class="size-3.5" />
              Payment disbursed
            </Badge>
          {/if}
        </Card.Action>
      </Card.Header>
      <Card.Content class="pt-0">
        {#if entry.status === "draft" || entry.status === "under_review"}
          <p class="text-sm text-base-content/60">
            Approval issues an invoice to the employee. Tasks remain in Done.
          </p>
        {:else if entry.status === "approved"}
          <p class="text-sm text-base-content/60">
            The invoice is available to the employee. Disbursement writes a
            ledger debit and notifies them.
          </p>
        {:else if entry.status === "paid"}
          <p class="text-sm text-base-content/60">
            This entry has been paid
            {#if entry.approved_at}
              · approved {formatDate(entry.approved_at)}{/if}.
          </p>
        {/if}
      </Card.Content>
    </Card.Root>

    <!-- Task breakdown data table (below the header card, full width) -->
    <Card.Root>
      <Card.Header>
        <Card.Title>Task Breakdown</Card.Title>
        <Card.Description>
          Approved tasks moved to Done during this cutoff, with the rate
          snapshot captured at approval.
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
                >This entry has no payable tasks.</Empty.Description
              >
            </Empty.Header>
          </Empty.Root>
        {:else}
          <DataTable
            data={tableData}
            totalAmount={formatCurrency(entry.total_amount)}
          />
          <Pagination
            page={lineItemsPage}
            pageSize={lineItemsPageSize}
            total={lineItemsTotal}
            {loading}
            pageSizeOptions={[10, 25, 50, 100]}
            onchange={setLineItemsPage}
            onpagesizechange={(size) => {
              lineItemsPageSize = size;
              setLineItemsPage(1);
            }}
          />
        {/if}
      </Card.Content>
    </Card.Root>
  {:else if loading}
    <Skeleton class="h-20 w-full" />
    <Skeleton class="h-64 w-full" />
  {/if}
</div>
