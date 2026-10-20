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
  const classes = $derived(cn("hq-item", `hq-item--${variant}`, `hq-item--${size}`, className));
</script>

{#if child}
  {@render child({ props: { ...rest, class: classes, href } })}
{:else if href}
  <a class={classes} {href} {...rest}>{@render children?.()}</a>
{:else}
  <div class={classes} {...rest}>{@render children?.()}</div>
{/if}

<style>
  .hq-item {
    display: flex;
    min-width: 0;
    align-items: center;
    gap: 10px;
    border: 1px solid transparent;
    border-radius: 9px;
    padding: 10px;
    color: inherit;
    text-decoration: none;
  }
  .hq-item--outline { border-color: var(--border); background: #fff; }
  .hq-item--muted { background: var(--muted); }
  .hq-item--image { padding: 6px; }
  .hq-item--sm { padding: 7px; font-size: 12px; }
  a.hq-item:hover { border-color: #d9e1ed; background: #f8faff; }
</style>
