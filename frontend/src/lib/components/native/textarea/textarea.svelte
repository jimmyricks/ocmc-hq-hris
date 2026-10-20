<script lang="ts">
  import type { HTMLTextareaAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";

  type Props = Omit<HTMLTextareaAttributes, "class" | "value"> & {
    value?: string;
    ref?: HTMLTextAreaElement | null;
    class?: string;
  };

  let {
    value = $bindable(""),
    ref = $bindable(null),
    class: className,
    ...rest
  }: Props = $props();
</script>

<textarea bind:this={ref} bind:value class={cn("hq-textarea", className)} {...rest}></textarea>

<style>
  .hq-textarea {
    width: 100%;
    min-height: 72px;
    border: 1px solid var(--input);
    border-radius: 8px;
    background: #fff;
    padding: 9px 11px;
    color: var(--foreground);
    font-size: 13px;
    line-height: 1.45;
    resize: vertical;
    transition: border-color 130ms ease, box-shadow 130ms ease;
  }
  .hq-textarea::placeholder {
    color: #8b96a6;
  }
  .hq-textarea:hover {
    border-color: #aeb9c9;
  }
  .hq-textarea:focus {
    border-color: var(--primary);
    outline: 3px solid rgb(120 149 232 / 22%);
  }
  .hq-textarea:disabled {
    background: var(--muted);
    color: var(--muted-foreground);
  }
</style>
