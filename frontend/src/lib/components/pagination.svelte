<script lang="ts">
  import ChevronLeftIcon from "@lucide/svelte/icons/chevron-left";
  import ChevronRightIcon from "@lucide/svelte/icons/chevron-right";
  import * as Select from "$lib/components/ui/select/index.js";

  let {
    page = 1,
    pageSize = 25,
    total = 0,
    loading = false,
    onchange,
    onpagesizechange,
    pageSizeOptions = [],
    showSummary = true,
  }: {
    page?: number;
    pageSize?: number;
    total?: number;
    loading?: boolean;
    onchange?: (page: number) => void;
    onpagesizechange?: (pageSize: number) => void;
    pageSizeOptions?: number[];
    showSummary?: boolean;
  } = $props();

  const pageCount = $derived(Math.max(1, Math.ceil(total / pageSize)));
  const currentPage = $derived(Math.min(Math.max(1, page), pageCount));
  const startItem = $derived(
    total === 0 ? 0 : (currentPage - 1) * pageSize + 1,
  );
  const endItem = $derived(Math.min(total, currentPage * pageSize));
  const pages = $derived.by(() => {
    const visiblePageCount = 5;
    const values: (number | "ellipsis")[] = [];

    if (pageCount <= visiblePageCount) {
      for (let value = 1; value <= pageCount; value++) values.push(value);
      return values;
    }

    if (currentPage <= 3) {
      values.push(1, 2, 3, 4, "ellipsis", pageCount);
    } else if (currentPage >= pageCount - 2) {
      values.push(1, "ellipsis");
      for (let value = pageCount - 3; value <= pageCount; value++) {
        values.push(value);
      }
    } else {
      values.push(
        1,
        "ellipsis",
        currentPage - 1,
        currentPage,
        currentPage + 1,
        "ellipsis",
        pageCount,
      );
    }

    return values;
  });

  function go(nextPage: number) {
    if (loading || nextPage === currentPage) return;
    onchange?.(Math.min(Math.max(1, nextPage), pageCount));
  }
</script>

<div
  class="flex flex-col gap-3 border-t border-base-300 px-2 py-3 sm:flex-row sm:items-center sm:justify-between"
>
  {#if showSummary}
    <p class="text-xs text-base-content/60" aria-live="polite">
      {#if total === 0}
        No records
      {:else}
        Showing {startItem}-{endItem} of {total}
      {/if}
    </p>
  {/if}

  <div class="flex flex-wrap items-center gap-3">
    {#if onpagesizechange && pageSizeOptions.length}
      <div class="flex items-center gap-2 text-xs text-base-content/60">
        <span>Rows</span>
        <Select.Root
          type="single"
          value={String(pageSize)}
          disabled={loading}
          onValueChange={(value) => onpagesizechange?.(Number(value))}
        >
          <Select.Trigger size="sm" class="w-20" aria-label="Rows per page">
            {pageSize}
          </Select.Trigger>
          <Select.Content portal>
            {#each pageSizeOptions as option (option)}
              <Select.Item value={String(option)} label={`${option} rows`}>
                {option}
              </Select.Item>
            {/each}
          </Select.Content>
        </Select.Root>
      </div>
    {/if}

    <nav class="join join-horizontal" aria-label="Pagination">
      <button
        type="button"
        class="join-item btn btn-sm btn-square"
        disabled={loading || currentPage <= 1}
        aria-label="Previous page"
        onclick={() => go(currentPage - 1)}
      >
        <ChevronLeftIcon size={15} aria-hidden="true" />
      </button>
      {#each pages as item, index (`${item}-${index}`)}
        {#if item === "ellipsis"}
          <button
            type="button"
            class="join-item btn btn-sm btn-disabled"
            disabled
            aria-hidden="true">…</button
          >
        {:else}
          <button
            type="button"
            class="join-item btn btn-sm"
            class:btn-active={item === currentPage}
            aria-label={`Page ${item}`}
            aria-current={item === currentPage ? "page" : undefined}
            onclick={() => go(item)}
          >
            {item}
          </button>
        {/if}
      {/each}
      <button
        type="button"
        class="join-item btn btn-sm btn-square"
        disabled={loading || currentPage >= pageCount}
        aria-label="Next page"
        onclick={() => go(currentPage + 1)}
      >
        <ChevronRightIcon size={15} aria-hidden="true" />
      </button>
    </nav>
  </div>
</div>
