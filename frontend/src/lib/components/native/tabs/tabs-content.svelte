<script lang="ts">
  import type { Snippet } from "svelte";
  import { Tabs as BitsTabs } from "bits-ui";
  import type { TabsContentProps } from "bits-ui";
  import { cn } from "$lib/utils.js";
  let {
    value,
    children,
    class: className,
    ...rest
  }: Omit<TabsContentProps, "children" | "class" | "value"> & {
    value: string;
    children?: Snippet;
    class?: string;
  } = $props();
</script>

<BitsTabs.Content {value} class={cn("hq-tabs__content", className)} {...rest}>
  {@render children?.()}
</BitsTabs.Content>

<style>
  :global(.hq-tabs__content) {
    margin-top: 18px;
    outline: 0;
  }
</style>
