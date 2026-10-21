<script lang="ts">
  import type { Snippet } from "svelte";
  import type { HTMLAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";
  let {
    children,
    size = "md",
    class: className,
    ...rest
  }: HTMLAttributes<HTMLElement> & {
    children?: Snippet;
    size?: "xs" | "sm" | "md" | "lg" | "xl";
    class?: string;
  } = $props();

  const sizeClasses: Record<string, string> = {
    xs: "tabs-xs",
    sm: "tabs-sm",
    md: "tabs-md",
    lg: "tabs-lg",
    xl: "tabs-xl",
  };
</script>

<div
  role="tablist"
  class={cn(
    "tabs tabs-box border border-base-300",
    sizeClasses[size],
    className,
  )}
  {...rest}
>
  {@render children?.()}
</div>
