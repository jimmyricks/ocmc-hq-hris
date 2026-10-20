<script lang="ts">
  import type { Snippet } from "svelte";
  import type { HTMLAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";
  let { children, class: className, ...rest }: HTMLAttributes<HTMLTableRowElement> & { children?: Snippet; class?: string } = $props();
</script>
<tr class={cn("hq-table__row", className)} {...rest}>{@render children?.()}</tr>
<style>.hq-table__row{border-bottom:1px solid #e8edf4;} .hq-table__row:hover{background:#fafbfe;} .hq-table__row:last-child{border-bottom:0;}</style>
