<script lang="ts">
  import type { Snippet } from "svelte";
  import type { HTMLAttributes } from "svelte/elements";
  let { children, ...rest }: HTMLAttributes<HTMLElement> & { children?: Snippet } = $props();
</script>
{@render children?.()}
