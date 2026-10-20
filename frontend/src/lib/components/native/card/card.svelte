<script lang="ts">
  import type { Snippet } from "svelte";
  import type { HTMLAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";
  let { children, class: className, ...rest }: HTMLAttributes<HTMLElement> & { children?: Snippet; class?: string } = $props();
</script>

<section class={cn("hq-card", className)} {...rest}>{@render children?.()}</section>

<style>
  .hq-card {
    border: 1px solid var(--border);
    border-radius: 10px;
    background: var(--card);
    color: var(--card-foreground);
    box-shadow: 0 1px 2px rgb(32 42 56 / 3%);
  }
</style>
