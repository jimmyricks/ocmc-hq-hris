<script lang="ts">
  import type { Snippet } from "svelte";
  import type { HTMLAttributes } from "svelte/elements";
  let {
    children,
    class: className = "",
    ...rest
  }: HTMLAttributes<HTMLTableSectionElement> & {
    children?: Snippet;
    class?: string;
  } = $props();
</script>

<tfoot class="border-t border-base-300 {className}" {...rest}>
  {@render children?.()}
</tfoot>
