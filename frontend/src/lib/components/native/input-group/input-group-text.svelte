<script lang="ts">
  import type { Snippet } from "svelte";
  import type { HTMLAttributes } from "svelte/elements";
  let { children, class: className = "", ...rest }: HTMLAttributes<HTMLElement> & { children?: Snippet; class?: string } = $props();
</script>
<span class="hq-input-group__text {className}" {...rest}>{@render children?.()}</span>
<style>.hq-input-group__text{font-size:12px;}</style>
