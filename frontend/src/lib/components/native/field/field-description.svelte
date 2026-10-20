<script lang="ts">
  import type { Snippet } from "svelte";
  import type { HTMLAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";
  let { children, class: className, ...rest }: HTMLAttributes<HTMLParagraphElement> & { children?: Snippet; class?: string } = $props();
</script>
<p class={cn("hq-field__description", className)} {...rest}>{@render children?.()}</p>
<style>.hq-field__description{margin:0;color:var(--muted-foreground);font-size:11px;line-height:1.45;}</style>
