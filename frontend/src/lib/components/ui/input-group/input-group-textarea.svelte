<script lang="ts">
  import type { HTMLTextareaAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";
  let {
    ref = $bindable(null),
    value = $bindable(""),
    class: className,
    ...rest
  }: HTMLTextareaAttributes & {
    ref?: HTMLTextAreaElement | null;
    class?: string;
  } = $props();
</script>

<textarea
  bind:this={ref}
  bind:value
  class={cn("textarea border-base-300 w-full", className)}
  {...rest}></textarea>
