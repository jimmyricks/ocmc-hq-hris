<script lang="ts">
  import type { Snippet } from "svelte";
  import type { HTMLAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";
  let {
    children,
    class: className,
    ...rest
  }: HTMLAttributes<HTMLParagraphElement> & {
    children?: Snippet;
    class?: string;
  } = $props();
</script>

<p class={cn("label text-xs whitespace-normal", className)} {...rest}>
  {@render children?.()}
</p>
