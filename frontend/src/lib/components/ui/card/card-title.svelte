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

<h3 class={cn("card-title text-base font-semibold", className)} {...rest}>
  {@render children?.()}
</h3>
