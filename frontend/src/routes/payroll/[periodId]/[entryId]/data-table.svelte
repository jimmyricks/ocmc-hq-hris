<script lang="ts">
  import * as Table from "$lib/components/ui/table/index.js";

  type LineItemRow = {
    id: string;
    taskTitle: string;
    taskTypeName?: string;
    submissionNotes?: string;
    rate: string;
    quantity: number;
    amount: string;
  };

  let { data, totalAmount }: { data: LineItemRow[]; totalAmount: string } =
    $props();
</script>

<div class="w-full">
  <div class="overflow-x-auto rounded-box border border-base-300 bg-base-100">
    <Table.Root class="table-zebra">
      <Table.Header>
        <Table.Row>
          <Table.Head>Task</Table.Head>
          <Table.Head>Submission Notes</Table.Head>
          <Table.Head class="text-right">Rate</Table.Head>
          <Table.Head class="text-right">Qty</Table.Head>
          <Table.Head class="text-right">Amount</Table.Head>
        </Table.Row>
      </Table.Header>
      <Table.Body>
        {#each data as row (row.id)}
          <Table.Row>
            <Table.Cell>
              <div class="flex flex-col gap-0.5">
                <span class="font-medium">{row.taskTitle}</span>
                {#if row.taskTypeName}
                  <span class="text-xs text-base-content/60">
                    {row.taskTypeName}
                  </span>
                {/if}
              </div>
            </Table.Cell>
            <Table.Cell>
              <span class="block max-w-64 truncate text-base-content/60">
                {row.submissionNotes ?? "—"}
              </span>
            </Table.Cell>
            <Table.Cell class="text-right tabular-nums">{row.rate}</Table.Cell>
            <Table.Cell class="text-right tabular-nums"
              >{row.quantity}</Table.Cell
            >
            <Table.Cell class="text-right font-medium tabular-nums">
              {row.amount}
            </Table.Cell>
          </Table.Row>
        {:else}
          <Table.Row>
            <Table.Cell colspan={5} class="h-24 text-center">
              No line items.
            </Table.Cell>
          </Table.Row>
        {/each}
      </Table.Body>
      <Table.Footer>
        <Table.Row class="bg-base-200/60 font-semibold">
          <Table.Cell colspan={4}>Total</Table.Cell>
          <Table.Cell class="text-right text-base tabular-nums">
            {totalAmount}
          </Table.Cell>
        </Table.Row>
      </Table.Footer>
    </Table.Root>
  </div>
</div>
