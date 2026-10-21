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
    variant === "icon" &&
      "grid size-10 place-items-center rounded-lg border border-base-300 bg-base-200 text-base-content/60",
    className,
  )}
  {...rest}
>
  {@render children?.()}
</div>
