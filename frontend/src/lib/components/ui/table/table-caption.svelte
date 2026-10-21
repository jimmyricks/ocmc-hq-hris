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

<caption
  class="px-3 py-2 text-left text-xs text-base-content/60 {className}"
  {...rest}
>
  {@render children?.()}
</caption>
