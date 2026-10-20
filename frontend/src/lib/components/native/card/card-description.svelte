<script lang="ts">
  import type { Snippet } from "svelte";
  import type { HTMLAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";
  let { children, class: className, ...rest }: HTMLAttributes<HTMLParagraphElement> & { children?: Snippet; class?: string } = $props();
</script>
<p class={cn("hq-card__description", className)} {...rest}>{@render children?.()}</p>
<style>.hq-card__description{margin:4px 0 0;color:var(--muted-foreground);font-size:12px;line-height:1.45;}</style>
