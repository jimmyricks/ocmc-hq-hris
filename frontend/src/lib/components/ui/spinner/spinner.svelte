<script lang="ts">
  import type { HTMLAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";
  let { class: className, ...rest }: HTMLAttributes<HTMLSpanElement> = $props();
</script>

<span
  class={cn("loading loading-spinner loading-sm text-primary", className)}
  aria-label="Loading"
  role="status"
  {...rest}
></span>
