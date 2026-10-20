<script lang="ts">
  import type { Snippet } from "svelte";
  import type { HTMLAttributes } from "svelte/elements";
  let { children, class: className = "", ...rest }: HTMLAttributes<HTMLTableSectionElement> & { children?: Snippet; class?: string } = $props();
</script>
<tfoot class="hq-table__footer {className}" {...rest}>{@render children?.()}</tfoot>
