<script lang="ts">
  import type { HTMLAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";
  let { class: className, ...rest }: HTMLAttributes<HTMLDivElement> = $props();
</script>

<div
  class={cn("skeleton min-h-3", className)}
  aria-hidden="true"
  {...rest}
></div>
