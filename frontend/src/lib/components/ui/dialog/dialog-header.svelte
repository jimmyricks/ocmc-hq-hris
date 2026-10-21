<script lang="ts">
  import type { Snippet } from "svelte";
  import type { HTMLAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";
  let {
    children,
    class: className,
    ...rest
  }: HTMLAttributes<HTMLElement> & {
    children?: Snippet;
    class?: string;
  } = $props();
</script>

<header class={cn("mb-4 grid gap-1", className)} {...rest}>
  {@render children?.()}
</header>
