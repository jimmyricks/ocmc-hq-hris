<script lang="ts">
  import type { Snippet } from "svelte";
  import type { HTMLAttributes } from "svelte/elements";
  let {
    children,
    class: className = "",
    ...rest
  }: HTMLAttributes<HTMLHeadingElement> & {
    children?: Snippet;
    class?: string;
  } = $props();
</script>

<h3 class="m-0 text-base font-semibold {className}" {...rest}>
  {@render children?.()}
</h3>
