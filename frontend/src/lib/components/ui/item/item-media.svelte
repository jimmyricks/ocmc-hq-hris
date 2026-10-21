<script lang="ts">
  import type { Snippet } from "svelte";
  import type { HTMLAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";
  let {
    children,
    variant = "default",
    class: className,
    ...rest
  }: HTMLAttributes<HTMLElement> & {
    children?: Snippet;
    variant?: string;
    class?: string;
  } = $props();
</script>

<div
  class={cn(
    "grid size-8 shrink-0 place-items-center rounded-lg text-base-content/60",
    variant === "icon" && "border border-base-300 bg-base-200",
    variant === "image" && "overflow-hidden",
    className,
  )}
  {...rest}
>
  {@render children?.()}
</div>
