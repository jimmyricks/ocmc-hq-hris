<script lang="ts">
  import type { Snippet } from "svelte";
  import type { HTMLAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";
  let {
    children,
    class: className,
    ...rest
  }: HTMLAttributes<HTMLTableSectionElement> & {
    children?: Snippet;
    class?: string;
  } = $props();
</script>

<tbody class={className} {...rest}>{@render children?.()}</tbody>
