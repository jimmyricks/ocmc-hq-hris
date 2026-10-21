<script lang="ts">
  import type { Snippet } from "svelte";
  import type { HTMLAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";
  let {
    children,
    class: className,
    ...rest
  }: HTMLAttributes<HTMLSpanElement> & {
    children?: Snippet;
    class?: string;
  } = $props();
</script>

<span
  class={cn(
    "avatar relative inline-flex size-8 shrink-0 items-center justify-center overflow-hidden rounded-full bg-primary/10 text-xs font-semibold text-primary",
    className,
  )}
  {...rest}>{@render children?.()}</span
>
