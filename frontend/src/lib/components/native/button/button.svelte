<script lang="ts">
  import type { Snippet } from "svelte";
  import type {
    HTMLAnchorAttributes,
    HTMLButtonAttributes,
  } from "svelte/elements";
  import { Button as BitsButton } from "bits-ui";
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
      | "link";
    size?: "default" | "sm" | "icon" | "icon-sm" | "lg";
    class?: string;
  } & Omit<HTMLButtonAttributes, "class"> &
    Omit<HTMLAnchorAttributes, "class" | "href">;

  let {
    children,
    href,
    type = "button",
    variant = "default",
    size = "default",
    class: className,
    disabled,
    ...rest
  }: Props = $props();
  const classes = $derived(
    cn(
      "hq-button",
      `hq-button--${variant === "danger" ? "destructive" : variant}`,
      `hq-button--${size}`,
      className,
    ),
  );
</script>

{#if href && !disabled}
  <BitsButton.Root {href} class={classes} {...rest}>
    {@render children?.()}
  </BitsButton.Root>
{:else}
  <BitsButton.Root {type} class={classes} {disabled} {...rest}>
    {@render children?.()}
  </BitsButton.Root>
{/if}

<style>
  :global(.hq-button) {
    display: inline-flex;
    min-height: 38px;
    align-items: center;
    justify-content: center;
    gap: 8px;
    border: 1px solid var(--border);
    border-radius: 8px;
    background: var(--primary);
    padding: 0 13px;
    color: var(--primary-foreground);
    font-size: 13px;
    font-weight: 650;
    line-height: 1;
    text-decoration: none;
    white-space: nowrap;
    cursor: pointer;
    transition:
      background 130ms ease,
      border-color 130ms ease,
      color 130ms ease,
      transform 130ms ease;
  }
  :global(.hq-button:hover) {
    background: #1f4fc4;
    border-color: #1f4fc4;
  }
  :global(.hq-button:active) {
    transform: translateY(1px);
  }
  :global(.hq-button--outline),
  :global(.hq-button--secondary),
  :global(.hq-button--ghost),
  :global(.hq-button--destructive),
  :global(.hq-button--link) {
    color: #344256;
  }
  :global(.hq-button--outline),
  :global(.hq-button--secondary) {
    background: #fff;
  }
  :global(.hq-button--secondary) {
    border-color: transparent;
    background: var(--secondary);
    color: var(--secondary-foreground);
  }
  :global(.hq-button--outline:hover) {
    border-color: #aab7c8;
    background: #f8faff;
  }
  :global(.hq-button--secondary:hover) {
    border-color: #dbe3ef;
    background: #e5ebf5;
  }
  :global(.hq-button--ghost) {
    border-color: transparent;
    background: transparent;
  }
  :global(.hq-button--ghost:hover) {
    border-color: #e3e9f2;
    background: #f5f7fa;
  }
  :global(.hq-button--destructive) {
    border-color: #efc6ca;
    background: #fff;
    color: #ad2635;
  }
  :global(.hq-button--destructive:hover) {
    border-color: #e2a6ad;
    background: #fff4f5;
  }
  :global(.hq-button--link) {
    min-height: auto;
    border: 0;
    background: transparent;
    padding: 0;
    color: var(--primary);
    text-decoration: underline;
    text-underline-offset: 3px;
  }
  :global(.hq-button--sm) {
    min-height: 32px;
    padding-inline: 10px;
    font-size: 12px;
  }
  :global(.hq-button--lg) {
    min-height: 42px;
    padding-inline: 16px;
  }
  :global(.hq-button--icon),
  :global(.hq-button--icon-sm) {
    padding: 0;
    aspect-ratio: 1;
  }
  :global(.hq-button--icon) {
    width: 38px;
  }
  :global(.hq-button--icon-sm) {
    width: 32px;
    min-height: 32px;
  }
  :global(.hq-button:disabled) {
    cursor: not-allowed;
    opacity: 0.55;
  }
</style>
