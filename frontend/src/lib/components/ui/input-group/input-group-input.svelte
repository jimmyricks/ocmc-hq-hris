<script lang="ts">
  import type { HTMLInputAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";
  let {
    ref = $bindable(null),
    value = $bindable(""),
    class: className,
    ...rest
  }: HTMLInputAttributes & {
    ref?: HTMLInputElement | null;
    class?: string;
  } = $props();
</script>

<input
  bind:this={ref}
  bind:value
  class={cn("input border-base-300 w-full", className)}
  {...rest}
/>
