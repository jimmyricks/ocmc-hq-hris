<script lang="ts">
  import type { Snippet } from "svelte";
  import type { HTMLAnchorAttributes, HTMLAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";

  type Props = {
    children?: Snippet;
    child?: Snippet<[{ props: Record<string, unknown> }]>;
    variant?: "default" | "outline" | "muted" | "image";
    size?: "default" | "sm";
    href?: string;
    class?: string;
  } & Omit<HTMLAttributes<HTMLElement>, "class"> &
    Omit<HTMLAnchorAttributes, "class" | "href">;

  let {
    children,
    child,
    variant = "default",
    size = "default",
    href,
    class: className,
    ...rest
  }: Props = $props();
  const classes = $derived(
    cn(
      "flex min-w-0 items-center gap-2.5 rounded-lg border border-transparent p-2.5 text-inherit no-underline",
      variant === "outline" && "border-base-300 bg-base-100",
      variant === "muted" && "bg-base-200",
      variant === "image" && "p-1.5",
      size === "sm" && "gap-2 p-2 text-sm",
      href && "hover:border-base-300 hover:bg-base-200",
      className,
    ),
  );
</script>

{#if child}
  {@render child({ props: { ...rest, class: classes, href } })}
{:else if href}
  <a class={classes} {href} {...rest}>{@render children?.()}</a>
{:else}
  <div class={classes} {...rest}>{@render children?.()}</div>
{/if}
