<script lang="ts">
  import type { Snippet } from "svelte";
  import type { HTMLAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";
  let {
    children,
    class: className,
    ...rest
  }: HTMLAttributes<HTMLTableSectionElement> & {
    children?: Snippet;
    class?: string;
  } = $props();
</script>

<thead
  class={cn(
    "bg-base-200 text-xs font-semibold uppercase tracking-wider text-base-content/60",
    className,
  )}
  {...rest}>{@render children?.()}</thead
>
