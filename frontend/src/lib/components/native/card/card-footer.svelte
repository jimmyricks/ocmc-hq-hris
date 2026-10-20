<script lang="ts">
  import type { Snippet } from "svelte";
  import type { HTMLAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";
  let { children, class: className, ...rest }: HTMLAttributes<HTMLElement> & { children?: Snippet; class?: string } = $props();
</script>
<footer class={cn("hq-card__footer", className)} {...rest}>{@render children?.()}</footer>
<style>.hq-card__footer{border-top:1px solid var(--border);padding:14px 22px;}</style>
