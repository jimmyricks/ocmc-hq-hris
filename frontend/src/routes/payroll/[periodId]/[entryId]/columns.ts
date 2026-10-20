import type { ColumnDef } from "@tanstack/table-core";
import { createRawSnippet } from "svelte";
import { renderSnippet } from "$lib/components/ui/data-table/index.js";

export type LineItemRow = {
  id: string;
  taskTitle: string;
  taskKey?: string;
  taskTypeName?: string;
  submissionNotes?: string;
  rate: string;
  quantity: number;
  amount: string;
};

export const columns: ColumnDef<LineItemRow>[] = [
  {
    accessorKey: "taskTitle",
    header: "Task",
    cell: ({ row }) => {
      const taskSnippet = createRawSnippet<[{ taskTitle: string; taskKey?: string; taskTypeName?: string }]>((get) => {
        const { taskTitle, taskKey, taskTypeName } = get();
        const subtitle = taskTypeName || taskKey;
        return {
          render: () =>
            `<div class="flex flex-col gap-0.5"><span class="font-medium">${taskTitle}</span>${subtitle ? `<span class="text-xs text-muted-foreground">${taskTypeName ?? ""}${taskTypeName && taskKey ? " · " : ""}${taskKey ? `<span class="font-mono">${taskKey}</span>` : ""}</span>` : ""}</div>`,
        };
      });
      return renderSnippet(taskSnippet, {
        taskTitle: row.original.taskTitle,
        taskKey: row.original.taskKey,
        taskTypeName: row.original.taskTypeName,
      });
    },
  },
  {
    accessorKey: "submissionNotes",
    header: "Submission Notes",
    cell: ({ row }) => {
      const notesSnippet = createRawSnippet<[{ notes: string }]>((get) => {
        const { notes } = get();
        return {
          render: () => `<span class="block truncate max-w-[16rem] text-muted-foreground">${notes}</span>`,
        };
      });
      return renderSnippet(notesSnippet, { notes: row.original.submissionNotes ?? "—" });
    },
  },
  {
    accessorKey: "rate",
    header: "Rate",
    cell: ({ row }) => {
      const rateSnippet = createRawSnippet<[{ rate: string }]>((get) => {
        const { rate } = get();
        return { render: () => `<span class="tabular-nums">${rate}</span>` };
      });
      return renderSnippet(rateSnippet, { rate: row.original.rate });
    },
  },
  {
    accessorKey: "quantity",
    header: "Qty",
    cell: ({ row }) => {
      const qtySnippet = createRawSnippet<[{ qty: number }]>((get) => {
        const { qty } = get();
        return { render: () => `<span class="tabular-nums">${qty}</span>` };
      });
      return renderSnippet(qtySnippet, { qty: row.original.quantity });
    },
  },
  {
    accessorKey: "amount",
    header: "Amount",
    cell: ({ row }) => {
      const amountSnippet = createRawSnippet<[{ amount: string }]>((get) => {
        const { amount } = get();
        return { render: () => `<span class="font-medium tabular-nums">${amount}</span>` };
      });
      return renderSnippet(amountSnippet, { amount: row.original.amount });
    },
  },
];
