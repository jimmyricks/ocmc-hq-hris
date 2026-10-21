<script lang="ts">
  import type { Snippet } from "svelte";
  import type { HTMLFieldsetAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";
  let {
    children,
    class: className,
    ...rest
  }: HTMLFieldsetAttributes & { children?: Snippet; class?: string } = $props();
</script>

<fieldset class={cn("fieldset min-w-0 gap-3", className)} {...rest}>
  {@render children?.()}
</fieldset>
