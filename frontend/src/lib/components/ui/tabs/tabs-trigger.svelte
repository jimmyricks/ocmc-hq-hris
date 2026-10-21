<script lang="ts">
  import { getContext, type Snippet } from "svelte";
  import type { HTMLButtonAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";
  import { TABS_CONTEXT, type TabsContext } from "./context.js";

  let {
    value,
    children,
    class: className,
    ...rest
  }: Omit<HTMLButtonAttributes, "class"> & {
    value: string;
    children?: Snippet;
    class?: string;
  } = $props();
  const tabs = getContext<TabsContext>(TABS_CONTEXT);
  const active = $derived(tabs.value === value);
</script>

<button
  type="button"
  role="tab"
  aria-selected={active}
  data-state={active ? "active" : "inactive"}
  class={cn("tab", active && "tab-active", className)}
  {...rest}
  onclick={(event) => {
    rest.onclick?.(event);
    if (!event.defaultPrevented) tabs.setValue(value);
  }}
>
  {@render children?.()}
</button>
