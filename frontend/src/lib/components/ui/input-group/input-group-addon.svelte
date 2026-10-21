<script lang="ts">
  import type { Snippet } from "svelte";
  import type { HTMLAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";
  type Align = "inline-start" | "inline-end" | "block-start" | "block-end";
  let {
    children,
    align = "inline-start",
    class: className,
    ...rest
  }: HTMLAttributes<HTMLElement> & {
    children?: Snippet;
    align?: Align;
    class?: string;
  } = $props();

  const alignClasses: Record<Align, string> = {
    "inline-start": "absolute inset-y-0 start-0 z-10 flex items-center ps-2.5",
    "inline-end": "absolute inset-y-0 end-0 z-10 flex items-center pe-2.5",
    "block-start":
      "join-item flex items-center gap-1.5 border-base-300 bg-base-100 px-3 py-1.5",
    "block-end":
      "join-item flex items-center justify-end gap-1.5 border-base-300 bg-base-100 px-3 py-1.5",
  };
</script>

<div
  class={cn("text-base-content/60", alignClasses[align], className)}
  {...rest}
>
  {@render children?.()}
</div>
