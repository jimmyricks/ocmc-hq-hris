<script lang="ts">
  import type { Snippet } from "svelte";
  import type { HTMLAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";

  let {
    children,
    variant = "default",
    size = "md",
    class: className,
    ...rest
  }: {
    children?: Snippet;
    variant?:
      | "default"
      | "secondary"
      | "destructive"
      | "outline"
      | "primary"
      | "ghost"
      | "info"
      | "success"
      | "warning"
      | "error";
    size?: "xs" | "sm" | "md" | "lg" | "xl";
    class?: string;
  } & Omit<HTMLAttributes<HTMLSpanElement>, "class"> = $props();

  const variantClasses: Record<string, string> = {
    default: "badge-soft badge-neutral",
    primary: "badge-soft badge-primary",
    secondary: "badge-soft badge-neutral",
    destructive: "badge-soft badge-error",
    error: "badge-soft badge-error",
    success: "badge-soft badge-success",
    warning: "badge-soft badge-warning",
    info: "badge-soft badge-info",
    outline: "badge-outline",
    ghost: "badge-ghost",
  };

  const sizeClasses: Record<string, string> = {
    xs: "badge-xs",
    sm: "badge-sm",
    md: "badge-md",
    lg: "badge-lg",
    xl: "badge-xl",
  };
</script>

<span
  class={cn("badge", sizeClasses[size], variantClasses[variant], className)}
  {...rest}
>
  {@render children?.()}
</span>
