<script lang="ts">
  import type { HTMLAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";
  let { class: className, ...rest }: HTMLAttributes<HTMLSpanElement> = $props();
</script>

<span class={cn("hq-spinner", className)} aria-label="Loading" role="status" {...rest}></span>

<style>
  .hq-spinner {
    display: inline-block;
    width: 18px;
    height: 18px;
    border: 2px solid #d7dfec;
    border-top-color: var(--primary);
    border-radius: 50%;
    animation: spin 720ms linear infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
</style>
