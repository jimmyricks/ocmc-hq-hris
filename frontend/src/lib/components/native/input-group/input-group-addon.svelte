<script lang="ts">
  import type { Snippet } from "svelte";
  import type { HTMLAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";
  let { children, align = "inline-end", class: className, ...rest }: HTMLAttributes<HTMLElement> & { children?: Snippet; align?: "inline-start" | "inline-end" | "block-start" | "block-end"; class?: string } = $props();
</script>
<div class={cn("hq-input-group__addon", `hq-input-group__addon--${align}`, className)} {...rest}>{@render children?.()}</div>
<style>
  .hq-input-group__addon{display:flex;align-items:center;gap:6px;color:var(--muted-foreground);}
  .hq-input-group__addon--inline-start{position:absolute;top:0;bottom:0;left:10px;}
  .hq-input-group__addon--inline-end{position:absolute;top:0;right:10px;bottom:0;}
  .hq-input-group__addon--block-start{border-bottom:1px solid #edf1f6;padding:7px 10px;}
  .hq-input-group__addon--block-end{justify-content:flex-end;border-top:1px solid #edf1f6;padding:7px 10px;}
</style>
