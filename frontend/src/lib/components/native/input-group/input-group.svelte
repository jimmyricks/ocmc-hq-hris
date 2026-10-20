<script lang="ts">
  import type { Snippet } from "svelte";
  import type { HTMLAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";
  let { children, class: className, ...rest }: HTMLAttributes<HTMLElement> & { children?: Snippet; class?: string } = $props();
</script>
<div class={cn("hq-input-group", className)} {...rest}>{@render children?.()}</div>
<style>
  .hq-input-group{position:relative;overflow:hidden;border:1px solid var(--input);border-radius:8px;background:#fff;transition:border-color 130ms ease,box-shadow 130ms ease;}
  .hq-input-group:focus-within{border-color:var(--primary);box-shadow:0 0 0 3px rgb(120 149 232 / 22%);}
  .hq-input-group :global(.hq-input),.hq-input-group :global(.hq-textarea){border:0;border-radius:0;box-shadow:none;}
  .hq-input-group :global(.hq-input:focus),.hq-input-group :global(.hq-textarea:focus){outline:0;}
</style>
