<script lang="ts">
  import type { Snippet } from "svelte";
  import type { HTMLAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";
  let { children, class: className, ...rest }: HTMLAttributes<HTMLElement> & { children?: Snippet; class?: string } = $props();
</script>
<header class={cn("hq-card__header", className)} {...rest}>{@render children?.()}</header>
<style>.hq-card__header{padding:20px 22px 14px;}</style>
