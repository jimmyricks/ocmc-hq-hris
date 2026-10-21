<script lang="ts">
  import type { Snippet } from "svelte";
  import type { HTMLThAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";
  let {
    children,
    class: className,
    ...rest
  }: HTMLThAttributes & { children?: Snippet; class?: string } = $props();
</script>

<th
  class={cn(
    "h-9 px-3 text-left text-xs font-semibold uppercase tracking-wider text-base-content/60",
    className,
  )}
  {...rest}
>
  {@render children?.()}
</th>
