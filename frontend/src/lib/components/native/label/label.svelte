<script lang="ts">
  import type { Snippet } from "svelte";
  import { Label as BitsLabel } from "bits-ui";
  import type { LabelRootProps } from "bits-ui";
  import { cn } from "$lib/utils.js";
  let {
    children,
    class: className,
    ...rest
  }: Omit<LabelRootProps, "children" | "class"> & {
    children?: Snippet;
    class?: string;
  } = $props();
</script>

<BitsLabel.Root class={cn("hq-label", className)} {...rest}>
  {@render children?.()}
</BitsLabel.Root>

<style>
  :global(.hq-label) {
    color: #425066;
    font-size: 12px;
    font-weight: 650;
  }
</style>
