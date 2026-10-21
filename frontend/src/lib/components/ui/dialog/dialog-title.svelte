<script lang="ts">
  import type { Snippet } from "svelte";
  import type { HTMLAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";
  let {
    children,
    class: className,
    ...rest
  }: HTMLAttributes<HTMLHeadingElement> & {
    children?: Snippet;
    class?: string;
  } = $props();
</script>

<h2 class={cn("m-0 text-lg font-semibold tracking-tight", className)} {...rest}>
  {@render children?.()}
</h2>
