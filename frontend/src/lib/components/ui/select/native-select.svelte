<script lang="ts">
  import type { Snippet } from "svelte";
  import type { HTMLSelectAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";

  let {
    children,
    value = $bindable(""),
    size = "md",
    class: className,
    ...rest
  }: Omit<HTMLSelectAttributes, "class" | "value" | "size"> & {
    children?: Snippet;
    value?: string;
    size?: "xs" | "sm" | "md" | "lg" | "xl";
    class?: string;
  } = $props();

  const sizeClasses: Record<string, string> = {
    xs: "select-xs",
    sm: "select-sm",
    md: "select-md",
    lg: "select-lg",
    xl: "select-xl",
  };
</script>

<select
  bind:value
  class={cn("select border-base-300 w-full", sizeClasses[size], className)}
  {...rest}
>
  {@render children?.()}
</select>
