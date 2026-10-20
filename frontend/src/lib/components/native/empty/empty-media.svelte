<script lang="ts">
  import type { Snippet } from "svelte";
  import type { HTMLAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";
  let { children, variant = "default", class: className, ...rest }: HTMLAttributes<HTMLElement> & { children?: Snippet; variant?: string; class?: string } = $props();
</script>
<div class={cn("hq-empty__media", variant === "icon" && "hq-empty__media--icon", className)} {...rest}>{@render children?.()}</div>
<style>
  .hq-empty__media--icon{display:grid;width:42px;height:42px;place-items:center;border:1px solid var(--border);border-radius:11px;background:var(--muted);color:var(--muted-foreground);}
</style>
