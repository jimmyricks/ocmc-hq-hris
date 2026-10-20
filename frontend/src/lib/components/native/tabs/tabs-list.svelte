<script lang="ts">
  import type { Snippet } from "svelte";
  import { Tabs as BitsTabs } from "bits-ui";
  import type { TabsListProps } from "bits-ui";
  import { cn } from "$lib/utils.js";
  let {
    children,
    class: className,
    ...rest
  }: Omit<TabsListProps, "children" | "class"> & {
    children?: Snippet;
    class?: string;
  } = $props();
</script>

<BitsTabs.List class={cn("hq-tabs__list", className)} {...rest}>
  {@render children?.()}
</BitsTabs.List>

<style>
  :global(.hq-tabs__list) {
    display: inline-flex;
    align-items: center;
    gap: 3px;
    border: 1px solid var(--border);
    border-radius: 9px;
    background: var(--muted);
    padding: 3px;
  }
</style>
