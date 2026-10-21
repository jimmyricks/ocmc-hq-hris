<script lang="ts">
  import type { Snippet } from "svelte";
  import type { HTMLAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";
  let {
    children,
    class: className,
    ...rest
  }: HTMLAttributes<HTMLLegendElement> & {
    children?: Snippet;
    class?: string;
  } = $props();
</script>

<legend class={cn("fieldset-legend text-sm", className)} {...rest}>
  {@render children?.()}
</legend>
