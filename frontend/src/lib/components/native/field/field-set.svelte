<script lang="ts">
  import type { Snippet } from "svelte";
  import type { HTMLFieldsetAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";
  let { children, class: className, ...rest }: HTMLFieldsetAttributes & { children?: Snippet; class?: string } = $props();
</script>
<fieldset class={cn("hq-fieldset", className)} {...rest}>{@render children?.()}</fieldset>
<style>.hq-fieldset{display:grid;gap:12px;min-width:0;margin:0;border:0;padding:0;}</style>
