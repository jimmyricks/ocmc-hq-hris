<script lang="ts">
  import type { Snippet } from "svelte";
  import type { HTMLAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";
  let { children, class: className, ...rest }: HTMLAttributes<HTMLElement> & { children?: Snippet; class?: string } = $props();
</script>
<div class={cn("hq-field-group", className)} {...rest}>{@render children?.()}</div>
<style>.hq-field-group{display:flex;flex-direction:column;gap:14px;}</style>
