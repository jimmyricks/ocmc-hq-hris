<script lang="ts">
  import type { HTMLAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";
  let { class: className, ...rest }: HTMLAttributes<HTMLDivElement> = $props();
</script>

<div class={cn("hq-skeleton", className)} aria-hidden="true" {...rest}></div>

<style>
  .hq-skeleton {
    min-height: 12px;
    border-radius: 7px;
    background: linear-gradient(90deg, #edf1f6 25%, #f8fafc 45%, #edf1f6 65%);
    background-size: 220% 100%;
    animation: skeleton-pulse 1.2s ease-in-out infinite;
  }
  @keyframes skeleton-pulse {
    to { background-position: -220% 0; }
  }
</style>
