<script lang="ts">
  import type { Snippet } from "svelte";
  import { Tabs as BitsTabs } from "bits-ui";
  import type { TabsRootProps } from "bits-ui";
  import { cn } from "$lib/utils.js";

  let {
    value = $bindable(""),
    onValueChange,
    children,
    class: className,
    ...rest
  }: Omit<TabsRootProps, "children" | "class" | "onValueChange" | "value"> & {
    value?: string;
    onValueChange?: (value: string) => void;
    children?: Snippet;
    class?: string;
  } = $props();
</script>

<BitsTabs.Root
  bind:value
  {onValueChange}
  class={cn("hq-tabs", className)}
  {...rest}
>
  {@render children?.()}
</BitsTabs.Root>
