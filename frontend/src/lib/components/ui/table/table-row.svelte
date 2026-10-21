<script lang="ts">
  import type { Snippet } from "svelte";
  import type { HTMLAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";
  let {
    children,
    class: className,
    ...rest
  }: HTMLAttributes<HTMLTableRowElement> & {
    children?: Snippet;
    class?: string;
  } = $props();
</script>

<tr class={cn("border-base-300 hover:bg-base-200/50", className)} {...rest}>
  {@render children?.()}
</tr>
