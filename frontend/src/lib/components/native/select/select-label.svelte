<script lang="ts">
  import type { Snippet } from "svelte";
  import type { HTMLAttributes } from "svelte/elements";
  let { children, class: className = "", ...rest }: HTMLAttributes<HTMLElement> & { children?: Snippet; class?: string } = $props();
</script>
<div class="hq-select__label {className}" {...rest}>{@render children?.()}</div>
<style>.hq-select__label{padding:7px 9px 5px;color:var(--muted-foreground);font-size:10px;font-weight:750;letter-spacing:.06em;text-transform:uppercase;}</style>
