<script lang="ts">
  import {
    type ColumnDef,
    type ColumnFiltersState,
    type PaginationState,
    type RowSelectionState,
    type SortingState,
    type VisibilityState,
    getCoreRowModel,
    getFilteredRowModel,
    getPaginationRowModel,
    getSortedRowModel,
  } from "@tanstack/table-core";
  import {
    createSvelteTable,
    FlexRender,
    renderComponent,
    renderSnippet,
  } from "$lib/components/ui/data-table/index.js";
  import DataTableCheckbox from "$lib/components/ui/data-table/data-table-checkbox.svelte";
  import * as Table from "$lib/components/ui/table/index.js";
  import { Button } from "$lib/components/ui/button/index.js";
  import * as DropdownMenu from "$lib/components/ui/dropdown-menu/index.js";
  import { Input } from "$lib/components/ui/input/index.js";
  import { Badge } from "$lib/components/ui/badge/index.js";
  import * as Pagination from "$lib/components/ui/pagination/index.js";
  import { createRawSnippet, untrack, type Snippet } from "svelte";
  import { OFFICIAL_CURRENCY } from "$lib/constants.js";

  export type FieldMeta = {
    key: string;
    title: string;
    type: string;
    required?: boolean;
    readonly?: boolean;
    hidden?: boolean;
    visible?: boolean;
    in_list_view?: boolean;
    sortable?: boolean;
    filterable?: boolean;
    options?: { value: string; label: string }[];
    default?: any;
    link_entity?: string | null;
    child_entity?: string | null;
    parent_entity?: string | null;
    placeholder?: string | null;
    description?: string | null;
    width?: number;
    align?: "left" | "center" | "right";
  };

  export type EntityMetaSvelte = {
    name: string;
    label: string;
    module: string;
    group?: string;
    icon?: string;
    title_field?: string;
    in_sidebar?: boolean;
    columns: FieldMeta[];
    fields: FieldMeta[];
    field_layout?: string[][];
    filters: FieldMeta[];
    search_fields?: string[];
    permissions?: Record<string, boolean>;
    actions?: {
      action: string;
      label: string;
      icon?: string;
      enabled?: boolean;
    }[];
    config?: {
      page_size?: number;
      page_sizes?: number[];
      default_sort?: { id: string; desc: boolean }[];
    };
  };

  type DataTableProps = {
    meta: EntityMetaSvelte;
    data: Record<string, any>[];
    searchField?: string;
    hiddenColumns?: string[];
    actions?: Snippet<[Record<string, any>]>;
    onRowClick?: (record: Record<string, any>) => void;
  };

  let {
    meta,
    data,
    searchField = "title",
    hiddenColumns = [],
    actions,
    onRowClick,
  }: DataTableProps = $props();

  function renderCell(
    field: FieldMeta,
    value: any,
    record?: Record<string, any>,
  ) {
    if (value === null || value === undefined) {
      return renderSnippet(emptySnippet, {});
    }

    if (field.type === "boolean") {
      return renderSnippet(booleanSnippet, { value });
    }

    if (field.type === "select" && field.options) {
      const option = field.options.find((o) => o.value === value);
      const label = option?.label || value;
      const labelSnippet = createRawSnippet<[]>(() => ({
        render: () => `<span>${label}</span>`,
      }));
      return renderComponent(Badge, {
        variant: "secondary",
        class: "rounded-none",
        children: labelSnippet,
      });
    }

    if (field.type === "email") {
      return renderSnippet(linkSnippet, {
        href: `mailto:${value}`,
        label: value,
      });
    }

    if (field.type === "link" && field.link_entity) {
      const linkLabel = record?._link_titles?.[field.key] ?? value;
      return renderSnippet(linkSnippet, {
        href: `/${field.link_entity}?id=${value}`,
        label: linkLabel,
      });
    }

    if (field.type === "date" || field.type === "datetime") {
      return renderSnippet(textSnippet, {
        value: formatDate(value, field.type === "datetime"),
      });
    }

    if (field.type === "currency") {
      return renderSnippet(textSnippet, { value: formatCurrency(value) });
    }

    if (field.type === "percent") {
      return renderSnippet(textSnippet, { value: `${value}%` });
    }

    return renderSnippet(textSnippet, { value: String(value) });
  }

  function formatDate(value: string, includeTime: boolean) {
    if (!value) return "";
    const date = new Date(value);
    if (isNaN(date.getTime())) return value;
    return (
      date.toLocaleDateString() +
      (includeTime ? " " + date.toLocaleTimeString() : "")
    );
  }

  function formatCurrency(value: number | string) {
    const amount = Number(value);
    if (!Number.isFinite(amount)) return String(value);
    return new Intl.NumberFormat("en-PH", {
      style: "currency",
      currency: OFFICIAL_CURRENCY,
    }).format(amount);
  }

  const emptySnippet = createRawSnippet<[]>(() => ({
    render: () => '<span class="text-muted-foreground">—</span>',
  }));

  const textSnippet = createRawSnippet<[{ value: string }]>((getValue) => {
    const { value } = getValue();
    return { render: () => `<span class="text-foreground">${value}</span>` };
  });

  const booleanSnippet = createRawSnippet<[{ value: boolean }]>((getValue) => {
    const { value } = getValue();
    const icon = value ? "✓" : "✗";
    return {
      render: () =>
        `<span class="text-muted-foreground" aria-label="${value}">${icon}</span>`,
    };
  });

  const linkSnippet = createRawSnippet<[{ href: string; label: string }]>(
    (getValue) => {
      const { href, label } = getValue();
      return {
        render: () =>
          `<a href="${href}" class="text-primary hover:underline">${label}</a>`,
      };
    },
  );

  function buildColumns(fields: FieldMeta[]): ColumnDef<Record<string, any>>[] {
    return [
      {
        id: "select",
        header: (ctx: any) =>
          renderComponent(DataTableCheckbox, {
            checked: ctx.table.getIsAllPageRowsSelected(),
            indeterminate:
              ctx.table.getIsSomePageRowsSelected() &&
              !ctx.table.getIsAllPageRowsSelected(),
            onCheckedChange: (value: boolean) =>
              ctx.table.toggleAllPageRowsSelected(!!value),
            "aria-label": "Select all",
          }),
        cell: (ctx: any) =>
          renderComponent(DataTableCheckbox, {
            checked: ctx.row.getIsSelected(),
            onCheckedChange: (value: boolean) =>
              ctx.row.toggleSelected(!!value),
            "aria-label": "Select row",
          }),
        enableSorting: false,
        enableHiding: false,
      },
      ...fields
        .filter((field) => field.in_list_view)
        .map((field) => ({
          accessorKey: field.key,
          header: field.title,
          cell: (ctx: any) =>
            renderCell(field, ctx.row.original[field.key], ctx.row.original),
          enableSorting: field.sortable,
          enableHiding: true,
        })),
      ...(actions
        ? [
            {
              id: "actions",
              header: "Actions",
              cell: (ctx: any) => renderSnippet(actions, ctx.row.original),
              enableSorting: false,
              enableHiding: false,
            },
          ]
        : []),
    ];
  }

  let pageSize = $derived(meta.config?.page_size || 20);
  let defaultSort = $derived(meta.config?.default_sort || []);
  let label = $derived(meta.label);

  let pagination = $state<PaginationState>({ pageIndex: 0, pageSize: 20 });
  let sorting = $state<SortingState>([]);
  let columnFilters = $state<ColumnFiltersState>([]);
  let rowSelection = $state<RowSelectionState>({});
  let columnVisibility = $state<VisibilityState>({});

  $effect(() => {
    const next: VisibilityState = {};
    for (const col of hiddenColumns) {
      if (columnVisibility[col] === undefined) {
        next[col] = false;
      }
    }
    if (Object.keys(next).length) {
      columnVisibility = { ...columnVisibility, ...next };
    }
  });
  let globalFilter = $state("");

  $effect(() => {
    const ps = pageSize;
    pagination = { ...untrack(() => pagination), pageSize: ps };
  });

  $effect(() => {
    sorting = defaultSort;
  });

  const columnFields = $derived(meta.columns || meta.fields || []);
  const columns = $derived(buildColumns(columnFields));
  const labelMap = $derived(new Map(columnFields.map((f) => [f.key, f.title])));

  const table = createSvelteTable({
    get data() {
      return data;
    },
    get columns() {
      return columns;
    },
    state: {
      get pagination() {
        return pagination;
      },
      get sorting() {
        return sorting;
      },
      get columnVisibility() {
        return columnVisibility;
      },
      get rowSelection() {
        return rowSelection;
      },
      get columnFilters() {
        return columnFilters;
      },
      get globalFilter() {
        return globalFilter;
      },
    },
    getCoreRowModel: getCoreRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    onPaginationChange: (updater: any) => {
      pagination =
        typeof updater === "function" ? updater(pagination) : updater;
    },
    onSortingChange: (updater: any) => {
      sorting = typeof updater === "function" ? updater(sorting) : updater;
    },
    onColumnFiltersChange: (updater: any) => {
      columnFilters =
        typeof updater === "function" ? updater(columnFilters) : updater;
    },
    onColumnVisibilityChange: (updater: any) => {
      columnVisibility =
        typeof updater === "function" ? updater(columnVisibility) : updater;
    },
    onRowSelectionChange: (updater: any) => {
      rowSelection =
        typeof updater === "function" ? updater(rowSelection) : updater;
    },
    onGlobalFilterChange: (updater: any) => {
      globalFilter =
        typeof updater === "function" ? updater(globalFilter) : updater;
    },
  });

  function onSearchInput(e: Event) {
    globalFilter = (e.target as HTMLInputElement).value;
  }
</script>

<div class="w-full space-y-4">
  <div class="flex items-center justify-between gap-4">
    <Input
      placeholder="Search {label}..."
      value={globalFilter}
      oninput={onSearchInput}
      class="max-w-sm"
    />
    <DropdownMenu.Root>
      <DropdownMenu.Trigger>
        {#snippet child({ props })}
          <Button {...props} variant="outline">Columns</Button>
        {/snippet}
      </DropdownMenu.Trigger>
      <DropdownMenu.Content
        align="end"
        class="max-h-[300px] min-w-[12rem] overflow-y-auto"
      >
        {#each table
          .getAllColumns()
          .filter((col: any) => col.getCanHide()) as column (column.id)}
          <DropdownMenu.CheckboxItem
            bind:checked={
              () => column.getIsVisible(), (v) => column.toggleVisibility(!!v)
            }
          >
            {labelMap.get(column.id) ?? column.id}
          </DropdownMenu.CheckboxItem>
        {/each}
      </DropdownMenu.Content>
    </DropdownMenu.Root>
  </div>
  <div class="border">
    <Table.Root>
      <Table.Header>
        {#each table.getHeaderGroups() as headerGroup (headerGroup.id)}
          <Table.Row>
            {#each headerGroup.headers as header (header.id)}
              <Table.Head class="[&:has([role=checkbox])]:ps-3">
                {#if !header.isPlaceholder}
                  <FlexRender
                    content={header.column.columnDef.header}
                    context={header.getContext()}
                  />
                {/if}
              </Table.Head>
            {/each}
          </Table.Row>
        {/each}
      </Table.Header>
      <Table.Body>
        {#each table.getRowModel().rows as row (row.id)}
          <Table.Row
            data-state={row.getIsSelected() && "selected"}
            class={onRowClick ? "cursor-pointer hover:bg-muted/40" : undefined}
            onclick={(e) => {
              if (!onRowClick) return;
              const target = e.target as HTMLElement;
              if (
                target.closest(
                  "button, input, a, [role=checkbox], [role=switch]",
                )
              )
                return;
              onRowClick(row.original);
            }}
          >
            {#each row.getVisibleCells() as cell (cell.id)}
              <Table.Cell class="[&:has([role=checkbox])]:ps-3">
                <FlexRender
                  content={cell.column.columnDef.cell}
                  context={cell.getContext()}
                />
              </Table.Cell>
            {/each}
          </Table.Row>
        {:else}
          <Table.Row>
            <Table.Cell
              colspan={columns.length}
              class="h-24 text-center text-muted-foreground"
            >
              No records found.
            </Table.Cell>
          </Table.Row>
        {/each}
      </Table.Body>
    </Table.Root>
  </div>

  <div class="flex items-center justify-between">
    <div class="text-muted-foreground text-sm">
      {table.getFilteredSelectedRowModel().rows.length} of
      {table.getFilteredRowModel().rows.length} row(s) selected.
    </div>
    <div class="flex items-center space-x-2">
      <Pagination.Root
        count={table.getFilteredRowModel().rows.length}
        page={pagination.pageIndex + 1}
        perPage={pagination.pageSize}
      >
        {#snippet children({ pages, currentPage })}
          <Pagination.Content>
            <Pagination.Item>
              <Pagination.Previous
                onclick={() => table.previousPage()}
                disabled={!table.getCanPreviousPage()}
              />
            </Pagination.Item>
            {#each pages as page (page.key)}
              {#if page.type === "ellipsis"}
                <Pagination.Item>
                  <Pagination.Ellipsis />
                </Pagination.Item>
              {:else}
                <Pagination.Item>
                  <Pagination.Link
                    {page}
                    isActive={currentPage === page.value}
                    onclick={() => table.setPageIndex(page.value - 1)}
                  >
                    {page.value}
                  </Pagination.Link>
                </Pagination.Item>
              {/if}
            {/each}
            <Pagination.Item>
              <Pagination.Next
                onclick={() => table.nextPage()}
                disabled={!table.getCanNextPage()}
              />
            </Pagination.Item>
          </Pagination.Content>
        {/snippet}
      </Pagination.Root>
    </div>
  </div>
</div>
