<script lang="ts">
  import type { Snippet } from "svelte";
  import type { HTMLAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";
  let { children, class: className, ...rest }: HTMLAttributes<HTMLSpanElement> & { children?: Snippet; class?: string } = $props();
</script>

<span class={cn("hq-avatar", className)} {...rest}>{@render children?.()}</span>

<style>
  .hq-avatar {
    position: relative;
    display: inline-flex;
    width: 34px;
    height: 34px;
    flex: none;
    align-items: center;
    justify-content: center;
    overflow: hidden;
    border: 1px solid #dce4f1;
    border-radius: 10px;
    background: #edf2ff;
    color: #2457d6;
    font-size: 11px;
    font-weight: 750;
  }
</style>
