<script lang="ts">
  import type { Snippet } from "svelte";
  import type { HTMLAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";
  let { children, class: className, ...rest }: HTMLAttributes<HTMLElement> & { children?: Snippet; class?: string } = $props();
</script>
<div class={cn("hq-item__actions", className)} {...rest}>{@render children?.()}</div>
<style>.hq-item__actions{display:flex;flex:none;align-items:center;gap:6px;}</style>
