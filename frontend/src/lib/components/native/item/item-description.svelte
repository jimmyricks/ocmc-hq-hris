<script lang="ts">
  import type { Snippet } from "svelte";
  import type { HTMLAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";
  let { children, class: className, ...rest }: HTMLAttributes<HTMLElement> & { children?: Snippet; class?: string } = $props();
</script>
<div class={cn("hq-item__description", className)} {...rest}>{@render children?.()}</div>
<style>.hq-item__description{color:var(--muted-foreground);font-size:11px;line-height:1.4;}</style>
