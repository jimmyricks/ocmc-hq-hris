<script lang="ts">
  import type { Snippet } from "svelte";
  import type {
    HTMLAnchorAttributes,
    HTMLButtonAttributes,
  } from "svelte/elements";
  import { cn } from "$lib/utils.js";

  type Props = {
    children?: Snippet;
    href?: string;
    type?: "button" | "submit" | "reset";
    variant?:
      | "default"
      | "primary"
      | "secondary"
      | "outline"
      | "ghost"
      | "destructive"
      | "danger"
      | "success"
      | "warning"
      | "info"
      | "link";
    size?: "xs" | "sm" | "md" | "lg" | "xl";
    icon?: boolean;
    class?: string;
  } & Omit<HTMLButtonAttributes, "class"> &
    Omit<HTMLAnchorAttributes, "class" | "href">;

  let {
    children,
    href,
    type = "button",
    variant = "default",
    size = "md",
    icon = false,
    class: className,
    disabled,
    ...rest
  }: Props = $props();

  const variantClasses: Record<NonNullable<Props["variant"]>, string> = {
    default: "btn-primary",
    primary: "btn-primary",
    secondary: "btn-soft btn-secondary",
    outline: "btn-outline border-base-300",
    ghost: "btn-ghost",
    destructive: "btn-soft btn-error",
    danger: "btn-soft btn-error",
    success: "btn-soft btn-success",
    warning: "btn-soft btn-warning",
    info: "btn-soft btn-info",
    link: "btn-link",
  };
  const sizeClasses: Record<NonNullable<Props["size"]>, string> = {
    xs: "btn-xs",
    sm: "btn-sm",
    md: "btn-md",
    lg: "btn-lg",
    xl: "btn-xl",
  };

  const classes = $derived(
    cn(
      "btn",
      variantClasses[variant === "danger" ? "danger" : variant],
      sizeClasses[size],
      icon && "btn-square",
      className,
    ),
  );
</script>

{#if href && !disabled}
  <a {href} class={classes} {...rest}>{@render children?.()}</a>
{:else}
  <button {type} class={classes} {disabled} {...rest}>
    {@render children?.()}
  </button>
{/if}
