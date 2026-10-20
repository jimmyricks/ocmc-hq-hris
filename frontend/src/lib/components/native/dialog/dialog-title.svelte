<script lang="ts">
  import type { Snippet } from "svelte";
  import type { HTMLAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";
  let { children, class: className, ...rest }: HTMLAttributes<HTMLHeadingElement> & { children?: Snippet; class?: string } = $props();
</script>
<h2 class={cn("hq-dialog__title", className)} {...rest}>{@render children?.()}</h2>
<style>.hq-dialog__title{margin:0;font-size:17px;font-weight:750;letter-spacing:-0.02em;}</style>
