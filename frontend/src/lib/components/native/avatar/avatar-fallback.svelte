<script lang="ts">
  import type { Snippet } from "svelte";
  import type { HTMLAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";
  let { children, class: className, ...rest }: HTMLAttributes<HTMLSpanElement> & { children?: Snippet; class?: string } = $props();
</script>

<span class={cn("hq-avatar__fallback", className)} {...rest}>{@render children?.()}</span>
