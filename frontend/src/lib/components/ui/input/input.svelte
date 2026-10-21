<script lang="ts">
  import type { HTMLInputAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";

  type Props = Omit<HTMLInputAttributes, "class" | "value" | "size"> & {
    value?: string | number | readonly string[];
    ref?: HTMLInputElement | null;
    size?: "xs" | "sm" | "md" | "lg" | "xl";
    class?: string;
  };

  let {
    value = $bindable(""),
    ref = $bindable(null),
    size = "md",
    class: className,
    ...rest
  }: Props = $props();

  const sizeClasses: Record<string, string> = {
    xs: "input-xs",
    sm: "input-sm",
    md: "input-md",
    lg: "input-lg",
    xl: "input-xl",
  };
</script>

<input
  bind:this={ref}
  bind:value
  class={cn("input border-base-300 w-full", sizeClasses[size], className)}
  {...rest}
/>
