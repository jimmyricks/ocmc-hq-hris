<script lang="ts">
  import type { Snippet } from "svelte";
  import { Tabs as BitsTabs } from "bits-ui";
  import type { TabsTriggerProps } from "bits-ui";
  import { cn } from "$lib/utils.js";

  let {
    value,
    children,
    class: className,
    ...rest
  }: Omit<TabsTriggerProps, "children" | "class" | "value"> & {
    value: string;
    children?: Snippet;
    class?: string;
  } = $props();
</script>

<BitsTabs.Trigger {value} class={cn("hq-tabs__trigger", className)} {...rest}>
  {@render children?.()}
</BitsTabs.Trigger>

<style>
  :global(.hq-tabs__trigger) {
    display: inline-flex;
    min-height: 29px;
    align-items: center;
    justify-content: center;
    gap: 6px;
    border: 0;
    border-radius: 6px;
    background: transparent;
    padding: 0 12px;
    color: var(--muted-foreground);
    font-size: 12px;
    font-weight: 650;
    cursor: pointer;
    white-space: nowrap;
  }
  :global(.hq-tabs__trigger:hover) {
    color: var(--foreground);
  }
  :global(.hq-tabs__trigger[data-state="active"]) {
    background: var(--card);
    color: var(--foreground);
    box-shadow: 0 1px 3px rgb(32 42 56 / 8%);
  }
  :global(.hq-tabs__trigger:disabled) {
    cursor: not-allowed;
    opacity: 0.55;
  }
</style>
