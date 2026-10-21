<script lang="ts">
  import type { Snippet } from "svelte";
  import type { HTMLButtonAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";
  let {
    children,
    size = "sm",
    icon = false,
    variant = "default",
    class: className,
    ...rest
  }: Omit<HTMLButtonAttributes, "class"> & {
    children?: Snippet;
    size?: "xs" | "sm" | "md" | "lg" | "xl";
    icon?: boolean;
    variant?: string;
    class?: string;
  } = $props();

  const variantClasses: Record<string, string> = {
    default: "btn-primary",
    primary: "btn-primary",
    secondary: "btn-soft btn-secondary",
    outline: "btn-outline border-base-300",
    ghost: "btn-ghost",
    destructive: "btn-soft btn-error",
    success: "btn-soft btn-success",
    warning: "btn-soft btn-warning",
    info: "btn-soft btn-info",
  };
  const sizeClasses: Record<string, string> = {
    xs: "btn-xs",
    sm: "btn-sm",
    md: "btn-md",
    lg: "btn-lg",
    xl: "btn-xl",
  };
</script>

<button
  type="button"
  class={cn(
    "btn",
    variantClasses[variant] ?? "btn-primary",
    sizeClasses[size] ?? "btn-sm",
    icon && "btn-square",
    className,
  )}
  {...rest}>{@render children?.()}</button
>
