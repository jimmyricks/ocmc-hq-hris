<script lang="ts">
  import type { Snippet } from "svelte";
  import type { HTMLAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";
  let { children, class: className, ...rest }: HTMLAttributes<HTMLParagraphElement> & { children?: Snippet; class?: string } = $props();
</script>
<p class={cn("hq-dialog__description", className)} {...rest}>{@render children?.()}</p>
<style>.hq-dialog__description{margin:0;color:var(--muted-foreground);font-size:12px;line-height:1.5;}</style>
