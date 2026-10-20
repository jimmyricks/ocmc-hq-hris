<script lang="ts">
  import type { HTMLAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";
  let { orientation = "horizontal", class: className, ...rest }: HTMLAttributes<HTMLHRElement> & { orientation?: "horizontal" | "vertical"; class?: string } = $props();
</script>

<hr class={cn("hq-separator", orientation === "vertical" && "hq-separator--vertical", className)} aria-orientation={orientation} {...rest} />

<style>
  .hq-separator {
    width: 100%;
    height: 1px;
    border: 0;
    background: var(--border);
  }
  .hq-separator--vertical {
    width: 1px;
    height: auto;
    align-self: stretch;
  }
</style>
