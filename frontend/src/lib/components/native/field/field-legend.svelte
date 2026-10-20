<script lang="ts">
  import type { Snippet } from "svelte";
  import type { HTMLAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";
  let { children, class: className, ...rest }: HTMLAttributes<HTMLLegendElement> & { children?: Snippet; class?: string } = $props();
</script>
<legend class={cn("hq-field__legend", className)} {...rest}>{@render children?.()}</legend>
<style>.hq-field__legend{font-size:13px;font-weight:700;}</style>
