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

<div
  class="px-2 py-1.5 text-xs font-semibold uppercase tracking-wider text-base-content/60 {className}"
  {...rest}
>
  {@render children?.()}
</div>
