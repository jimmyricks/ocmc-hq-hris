<script lang="ts">
  import type { Snippet } from "svelte";
  import type { HTMLAttributes } from "svelte/elements";
  let { children, class: className = "", ...rest }: HTMLAttributes<HTMLParagraphElement> & { children?: Snippet; class?: string } = $props();
</script>
<p class="hq-empty__description {className}" {...rest}>{@render children?.()}</p>
<style>.hq-empty__description{max-width:420px;margin:0;color:var(--muted-foreground);font-size:12px;line-height:1.5;}</style>
