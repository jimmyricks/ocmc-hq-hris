<script lang="ts">
  import type { Snippet } from "svelte";
  import type { HTMLTdAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";
  let { children, class: className, ...rest }: HTMLTdAttributes & { children?: Snippet; class?: string } = $props();
</script>
<td class={cn("hq-table__cell", className)} {...rest}>{@render children?.()}</td>
<style>.hq-table__cell{padding:10px 12px;vertical-align:middle;}</style>
