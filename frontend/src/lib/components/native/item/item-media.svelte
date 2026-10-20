<script lang="ts">
  import type { Snippet } from "svelte";
  import type { HTMLAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";
  let { children, variant = "default", class: className, ...rest }: HTMLAttributes<HTMLElement> & { children?: Snippet; variant?: string; class?: string } = $props();
</script>
<div class={cn("hq-item__media", variant === "icon" && "hq-item__media--icon", variant === "image" && "hq-item__media--image", className)} {...rest}>{@render children?.()}</div>
<style>
  .hq-item__media{display:grid;width:34px;height:34px;flex:none;place-items:center;border-radius:8px;color:var(--muted-foreground);}
  .hq-item__media--icon{border:1px solid var(--border);background:var(--muted);}
  .hq-item__media--image{overflow:hidden;}
</style>
