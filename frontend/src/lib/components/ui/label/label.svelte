<script lang="ts">
  import type { Snippet } from "svelte";
  import type { HTMLLabelAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";
  let {
    children,
    class: className,
    ...rest
  }: HTMLLabelAttributes & { children?: Snippet; class?: string } = $props();
</script>

<label
  class={cn("label-text font-semibold text-base-content", className)}
  {...rest}>{@render children?.()}</label
>
