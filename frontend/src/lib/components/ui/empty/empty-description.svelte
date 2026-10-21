<script lang="ts">
  import type { Snippet } from "svelte";
  import type { HTMLAttributes } from "svelte/elements";
  let {
    children,
    class: className = "",
    ...rest
  }: HTMLAttributes<HTMLParagraphElement> & {
    children?: Snippet;
    class?: string;
  } = $props();
</script>

<p
  class="m-0 max-w-md text-sm leading-5 text-base-content/60 {className}"
  {...rest}
>
  {@render children?.()}
</p>
