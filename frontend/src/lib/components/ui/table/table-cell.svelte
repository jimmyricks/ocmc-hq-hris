<script lang="ts">
  import type { Snippet } from "svelte";
  import type { HTMLTdAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";
  let {
    children,
    class: className,
    ...rest
  }: HTMLTdAttributes & { children?: Snippet; class?: string } = $props();
</script>

<td class={cn("px-3 py-2.5 align-middle", className)} {...rest}>
  {@render children?.()}
</td>
