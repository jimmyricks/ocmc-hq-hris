<script lang="ts">
  import type { Snippet } from "svelte";
  import type { HTMLAttributes } from "svelte/elements";
  let {
    children,
    class: className = "",
    ...rest
  }: HTMLAttributes<HTMLElement> & {
    children?: Snippet;
    class?: string;
  } = $props();
</script>

<div class="mt-2 border-t border-base-300 pt-2 {className}" {...rest}>
  {@render children?.()}
</div>
