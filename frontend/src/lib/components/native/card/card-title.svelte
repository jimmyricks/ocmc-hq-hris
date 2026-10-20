<script lang="ts">
  import type { Snippet } from "svelte";
  import type { HTMLAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";
  let { children, class: className, ...rest }: HTMLAttributes<HTMLHeadingElement> & { children?: Snippet; class?: string } = $props();
</script>
<h3 class={cn("hq-card__title", className)} {...rest}>{@render children?.()}</h3>
<style>.hq-card__title{margin:0;color:var(--foreground);font-size:15px;font-weight:700;letter-spacing:-0.015em;}</style>
