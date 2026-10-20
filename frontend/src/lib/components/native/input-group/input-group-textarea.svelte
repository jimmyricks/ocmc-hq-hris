<script lang="ts">
  import type { HTMLTextareaAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";
  let {
    value = $bindable(""),
    ref = $bindable(null),
    class: className,
    ...rest
  }: Omit<HTMLTextareaAttributes, "value" | "class"> & {
    value?: string;
    ref?: HTMLTextAreaElement | null;
    class?: string;
  } = $props();
</script>

<textarea
  bind:this={ref}
  bind:value
  class={cn("hq-input-group__textarea", className)}
  {...rest}></textarea>

<style>
  .hq-input-group__textarea {
    width: 100%;
    min-height: 72px;
    border: 0;
    background: transparent;
    padding: 9px 11px;
    font-size: 13px;
    line-height: 1.45;
    resize: vertical;
    outline: 0;
  }
</style>
