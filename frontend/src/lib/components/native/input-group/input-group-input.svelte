<script lang="ts">
  import type { HTMLInputAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";
  let {
    value = $bindable(""),
    ref = $bindable(null),
    class: className,
    ...rest
  }: Omit<HTMLInputAttributes, "value" | "class"> & {
    value?: string | number | readonly string[];
    ref?: HTMLInputElement | null;
    class?: string;
  } = $props();
</script>

<input bind:this={ref} bind:value class={cn("hq-input", className)} {...rest} />

<style>
  .hq-input {
    width: 100%;
    min-height: 38px;
    background: transparent;
    padding: 0 11px;
    font-size: 13px;
    outline: 0;
  }
</style>
