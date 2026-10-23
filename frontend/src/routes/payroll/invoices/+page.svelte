<script lang="ts">
  import { browser } from "$app/environment";
  import { goto } from "$app/navigation";
  import { getToken } from "$lib/auth";
  import { toast } from "$lib/notifications";
  import { OFFICIAL_CURRENCY } from "$lib/constants.js";
  import { payrollApi } from "$lib/payroll/api.js";
  import type { PayrollInvoice } from "$lib/payroll/types.js";
  import Pagination from "$lib/components/pagination.svelte";

  import * as Card from "$lib/components/ui/card/index.js";
  import * as Empty from "$lib/components/ui/empty/index.js";
  import { Badge } from "$lib/components/ui/badge/index.js";
  import { Skeleton } from "$lib/components/ui/skeleton/index.js";

  import ReceiptTextIcon from "@lucide/svelte/icons/receipt-text";

  let invoices = $state<PayrollInvoice[]>([]);
  let page = $state(1);
  let pageSize = $state(25);
  let total = $state(0);
  let loading = $state(true);

  function formatCurrency(value: number | string | undefined): string {
    return new Intl.NumberFormat("en-PH", {
      style: "currency",
      currency: OFFICIAL_CURRENCY,
    }).format(Number(value ?? 0));
  }

  function formatDate(value?: string): string {
    return value ? value.split("T")[0] : "—";
  }

  $effect(() => {
    const currentPage = page;
    const currentPageSize = pageSize;
    if (!browser) return;
    if (!getToken()) {
      goto("/login");
      return;
    }
    void loadInvoices(currentPage, currentPageSize);
  });

  async function loadInvoices(currentPage: number, currentPageSize: number) {
    loading = true;
    try {
      const result = await payrollApi.getMyInvoicesPage(
        currentPage,
        currentPageSize,
      );
      if (page === currentPage && pageSize === currentPageSize) {
        invoices = result.items;
        total = result.total;
        page = result.page;
      }
    } catch (error: any) {
      toast.error(error.message || "Failed to load invoices");
    } finally {
      if (page === currentPage && pageSize === currentPageSize) loading = false;
    }
  }

  function setPage(targetPage: number) {
    page = targetPage;
  }
</script>

<div class="flex flex-col gap-6">
  <div>
    <h1 class="text-2xl font-bold tracking-tight">My invoices</h1>
    <p class="mt-1 text-sm text-base-content/60">
      Approved payroll invoices and their task-by-task breakdowns.
    </p>
  </div>

  {#if loading}
    {#each Array.from({ length: 2 }) as _, index (index)}
      <Skeleton class="h-48 w-full" />
    {/each}
  {:else if invoices.length === 0}
    <Card.Root>
      <Card.Content class="pt-6">
        <Empty.Root>
          <Empty.Media variant="icon"><ReceiptTextIcon /></Empty.Media>
          <Empty.Header>
            <Empty.Title>No invoices yet</Empty.Title>
            <Empty.Description>
              Invoices will appear here after HR approves your payroll for a
              cutoff.
            </Empty.Description>
          </Empty.Header>
        </Empty.Root>
      </Card.Content>
    </Card.Root>
  {:else}
    <div class="flex flex-col gap-4">
      {#each invoices as invoice (invoice.id)}
        <Card.Root>
          <Card.Header>
            <div class="flex flex-wrap items-start justify-between gap-3">
              <div>
                <Card.Title>{invoice.invoice_number}</Card.Title>
                <Card.Description>
                  {invoice.period_label ?? invoice.payroll_period_id}
                  · {formatDate(invoice.period_start_date)}–{formatDate(
                    invoice.period_end_date,
                  )}
                  · Issued {formatDate(invoice.issued_at)}
                </Card.Description>
              </div>
              <Badge
                variant={invoice.status === "paid" ? "default" : "secondary"}
              >
                {invoice.status === "paid" ? "Paid" : "Issued"}
              </Badge>
            </div>
          </Card.Header>
          <Card.Content>
            <div class="overflow-x-auto rounded-box border border-base-300">
              <table class="table table-zebra">
                <thead>
                  <tr>
                    <th>Task</th>
                    <th>Task type</th>
                    <th class="text-right">Rate</th>
                    <th class="text-right">Qty</th>
                    <th class="text-right">Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {#each invoice.line_items as line (line.id)}
                    <tr>
                      <td>
                        <div class="font-medium">{line.task_title}</div>
                        {#if line.submission_notes}
                          <div
                            class="max-w-72 truncate text-xs text-base-content/60"
                          >
                            {line.submission_notes}
                          </div>
                        {/if}
                      </td>
                      <td>{line.task_type_name ?? "—"}</td>
                      <td class="text-right tabular-nums">
                        {formatCurrency(line.rate)}
                      </td>
                      <td class="text-right tabular-nums"
                        >{line.quantity ?? 1}</td
                      >
                      <td class="text-right font-medium tabular-nums">
                        {formatCurrency(line.amount)}
                      </td>
                    </tr>
                  {:else}
                    <tr>
                      <td colspan={5} class="text-center text-base-content/60">
                        No task details available.
                      </td>
                    </tr>
                  {/each}
                </tbody>
              </table>
            </div>
            <div
              class="mt-4 flex justify-end gap-8 border-t border-base-300 pt-4"
            >
              <span class="text-sm text-base-content/60">
                {invoice.total_tasks}
                {invoice.total_tasks === 1 ? "task" : "tasks"}
              </span>
              <span class="text-lg font-bold tabular-nums">
                Total {formatCurrency(invoice.total_amount)}
              </span>
            </div>
          </Card.Content>
        </Card.Root>
      {/each}
      <Pagination
        {page}
        {pageSize}
        {total}
        {loading}
        pageSizeOptions={[10, 25, 50]}
        onchange={setPage}
        onpagesizechange={(size) => {
          pageSize = size;
          page = 1;
        }}
      />
    </div>
  {/if}
</div>
