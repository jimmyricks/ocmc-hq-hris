<script lang="ts">
  import type { Snippet } from "svelte";
  import type { HTMLAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";
  let { children, class: className, ...rest }: HTMLAttributes<HTMLTableSectionElement> & { children?: Snippet; class?: string } = $props();
</script>
<thead class={cn("hq-table__header", className)} {...rest}>{@render children?.()}</thead>
<style>.hq-table__header{background:#f7f9fc;color:#69778d;}</style>
