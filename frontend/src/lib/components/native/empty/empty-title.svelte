<script lang="ts">
  import type { Snippet } from "svelte";
  import type { HTMLAttributes } from "svelte/elements";
  let { children, class: className = "", ...rest }: HTMLAttributes<HTMLHeadingElement> & { children?: Snippet; class?: string } = $props();
</script>
<h3 class="hq-empty__title {className}" {...rest}>{@render children?.()}</h3>
<style>.hq-empty__title{margin:0;font-size:14px;font-weight:700;}</style>
