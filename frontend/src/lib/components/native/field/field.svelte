<script lang="ts">
  import type { Snippet } from "svelte";
  import type { HTMLAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";
  let { children, class: className, ...rest }: HTMLAttributes<HTMLElement> & { children?: Snippet; class?: string } = $props();
</script>
<div class={cn("hq-field", className)} {...rest}>{@render children?.()}</div>
<style>.hq-field{display:flex;flex-direction:column;gap:6px;min-width:0;}</style>
