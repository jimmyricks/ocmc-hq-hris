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

<footer
  class={cn(
    "flex flex-row flex-wrap items-center gap-2 border-t border-base-300 p-5",
    className,
  )}
  {...rest}
>
  {@render children?.()}
</footer>
