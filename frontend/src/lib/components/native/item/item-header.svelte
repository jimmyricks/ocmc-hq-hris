<script lang="ts">
  import type { Snippet } from "svelte";
  import type { HTMLAttributes } from "svelte/elements";
  let { children, class: className = "", ...rest }: HTMLAttributes<HTMLElement> & { children?: Snippet; class?: string } = $props();
</script>
<div class="hq-item__header {className}" {...rest}>{@render children?.()}</div>
<style>.hq-item__header{display:flex;align-items:center;gap:8px;}</style>
