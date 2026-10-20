<script lang="ts">
  import type { HTMLInputAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";

  type Props = Omit<HTMLInputAttributes, "class" | "value"> & {
    value?: string | number | readonly string[];
    ref?: HTMLInputElement | null;
    class?: string;
  };

  let {
    value = $bindable(""),
    ref = $bindable(null),
    class: className,
    ...rest
  }: Props = $props();
</script>

<input bind:this={ref} bind:value class={cn("hq-input", className)} {...rest} />

<style>
  .hq-input {
    width: 100%;
    min-height: 38px;
    border: 1px solid var(--input);
    border-radius: 8px;
    background: #fff;
    padding: 0 11px;
    color: var(--foreground);
    font-size: 13px;
    transition: border-color 130ms ease, box-shadow 130ms ease;
  }
  .hq-input::placeholder {
    color: #8b96a6;
  }
  .hq-input:hover {
    border-color: #aeb9c9;
  }
  .hq-input:focus {
    border-color: var(--primary);
    outline: 3px solid rgb(120 149 232 / 22%);
  }
  .hq-input:disabled {
    background: var(--muted);
    color: var(--muted-foreground);
  }
</style>
