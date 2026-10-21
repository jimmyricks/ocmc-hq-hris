<script lang="ts">
  import { getContext, type Snippet } from "svelte";
  import type { HTMLAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";
  import { TABS_CONTEXT, type TabsContext } from "./context.js";
  let {
    value,
    children,
    class: className,
    ...rest
  }: HTMLAttributes<HTMLElement> & {
    value: string;
    children?: Snippet;
    class?: string;
  } = $props();
  const tabs = getContext<TabsContext>(TABS_CONTEXT);
</script>

{#if tabs.value === value}
  <div role="tabpanel" class={cn("mt-4 outline-none", className)} {...rest}>
    {@render children?.()}
  </div>
{/if}
