<script lang="ts">
  import type { Snippet } from "svelte";
  import type { HTMLThAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";
  let { children, class: className, ...rest }: HTMLThAttributes & { children?: Snippet; class?: string } = $props();
</script>
<th class={cn("hq-table__head", className)} {...rest}>{@render children?.()}</th>
<style>.hq-table__head{height:34px;padding:0 12px;font-size:10px;font-weight:750;letter-spacing:0.06em;text-align:left;text-transform:uppercase;white-space:nowrap;}</style>
