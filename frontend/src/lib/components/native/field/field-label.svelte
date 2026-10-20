<script lang="ts">
  import type { Snippet } from "svelte";
  import type { HTMLLabelAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";
  let { children, class: className, ...rest }: HTMLLabelAttributes & { children?: Snippet; class?: string } = $props();
</script>
<label class={cn("hq-field__label", className)} {...rest}>{@render children?.()}</label>
<style>.hq-field__label{color:#425066;font-size:12px;font-weight:650;}</style>
