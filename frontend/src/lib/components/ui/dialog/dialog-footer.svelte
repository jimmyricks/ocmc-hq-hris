<script lang="ts">
  import type { Snippet } from "svelte";
  import type { HTMLAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";
  let {
    children,
    class: className,
    ...rest
  }: HTMLAttributes<HTMLElement> & {
    children?: Snippet;
    class?: string;
  } = $props();
</script>

<footer class={cn(" flex flex-wrap justify-end gap-2", className)} {...rest}>
  {@render children?.()}
</footer>
