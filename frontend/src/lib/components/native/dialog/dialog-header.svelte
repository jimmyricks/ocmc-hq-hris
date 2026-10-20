<script lang="ts">
  import type { Snippet } from "svelte";
  import type { HTMLAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";
  let { children, class: className, ...rest }: HTMLAttributes<HTMLElement> & { children?: Snippet; class?: string } = $props();
</script>
<header class={cn("hq-dialog__header", className)} {...rest}>{@render children?.()}</header>
<style>.hq-dialog__header{display:grid;gap:4px;margin-bottom:16px;}</style>
