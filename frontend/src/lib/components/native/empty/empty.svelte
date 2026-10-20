<script lang="ts">
  import type { Snippet } from "svelte";
  import type { HTMLAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";
  let { children, class: className, ...rest }: HTMLAttributes<HTMLElement> & { children?: Snippet; class?: string } = $props();
</script>
<div class={cn("hq-empty", className)} {...rest}>{@render children?.()}</div>
<style>.hq-empty{display:grid;justify-items:center;gap:10px;padding:36px 18px;text-align:center;}</style>
