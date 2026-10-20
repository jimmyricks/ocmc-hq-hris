<script lang="ts">
  import type { Snippet } from "svelte";
  import type { HTMLAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";
  let { children, class: className, ...rest }: HTMLAttributes<HTMLElement> & { children?: Snippet; class?: string } = $props();
</script>
<div class={cn("hq-card__action", className)} {...rest}>{@render children?.()}</div>
<style>.hq-card__action{margin-left:auto;}</style>
