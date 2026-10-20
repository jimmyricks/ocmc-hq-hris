<script lang="ts">
  import type { Snippet } from "svelte";
  import type { HTMLAttributes } from "svelte/elements";
  let { children, class: className = "", ...rest }: HTMLAttributes<HTMLElement> & { children?: Snippet; class?: string } = $props();
</script>
<div class="hq-field__title {className}" {...rest}>{@render children?.()}</div>
<style>.hq-field__title{font-size:13px;font-weight:700;}</style>
