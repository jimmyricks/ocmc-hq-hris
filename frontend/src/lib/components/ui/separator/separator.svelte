<script lang="ts">
  import type { HTMLAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";
  let {
    orientation = "horizontal",
    class: className,
    ...rest
  }: HTMLAttributes<HTMLHRElement> & {
    orientation?: "horizontal" | "vertical";
    class?: string;
  } = $props();
</script>

<hr
  class={cn(
    orientation === "horizontal"
      ? "my-2 h-px w-full border-0 bg-base-300"
      : "mx-2 h-full w-px self-stretch border-0 bg-base-300",
    className,
  )}
  aria-orientation={orientation}
  {...rest}
/>
