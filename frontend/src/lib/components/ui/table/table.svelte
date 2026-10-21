<script lang="ts">
  import type { Snippet } from "svelte";
  import type { HTMLTableAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";
  let {
    children,
    class: className,
    ...rest
  }: HTMLTableAttributes & { children?: Snippet; class?: string } = $props();
</script>

<table class={cn("table", className)} {...rest}>
  {@render children?.()}
</table>
