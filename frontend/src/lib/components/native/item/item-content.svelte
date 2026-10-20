<script lang="ts">
  import type { Snippet } from "svelte";
  import type { HTMLAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";
  let { children, class: className, ...rest }: HTMLAttributes<HTMLElement> & { children?: Snippet; class?: string } = $props();
</script>
<div class={cn("hq-item__content", className)} {...rest}>{@render children?.()}</div>
<style>.hq-item__content{display:grid;min-width:0;flex:1;gap:2px;}</style>
