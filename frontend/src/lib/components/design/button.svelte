<script lang="ts">
  import type { Snippet } from "svelte";
  import type {
    HTMLButtonAttributes,
    HTMLAnchorAttributes,
  } from "svelte/elements";

  type Props = {
    children?: Snippet;
    href?: string;
    type?: "button" | "submit" | "reset";
    variant?: "primary" | "outline" | "quiet" | "danger";
    size?: "sm" | "md";
    class?: string;
  } & Omit<HTMLButtonAttributes, "class"> &
    Omit<HTMLAnchorAttributes, "class" | "href">;

  let {
    children,
    href,
    type = "button",
    variant = "outline",
    size = "md",
    class: className = "",
    ...rest
  }: Props = $props();
</script>

{#if href}
  <a
    class="ds-button ds-button--{variant} ds-button--{size} {className}"
    {href}
    {...rest}
  >
    {@render children?.()}
  </a>
{:else}
  <button
    {type}
    class="ds-button ds-button--{variant} ds-button--{size} {className}"
    {...rest}
  >
    {@render children?.()}
  </button>
{/if}

<style>
  .ds-button {
    display: inline-flex;
    min-height: 38px;
    align-items: center;
    justify-content: center;
    gap: 8px;
    border: 1px solid #cbd3df;
    border-radius: 8px;
    background: #fff;
    padding: 0 13px;
    color: #344256;
    font-size: 13px;
    font-weight: 650;
    line-height: 1;
    text-decoration: none;
    white-space: nowrap;
    cursor: pointer;
    transition:
      background 130ms ease,
      border-color 130ms ease,
      transform 130ms ease;
  }
  .ds-button:hover {
    border-color: #aab7c8;
    background: #f8faff;
  }
  .ds-button:active {
    transform: translateY(1px);
  }
  .ds-button--primary {
    border-color: #2457d6;
    background: #2457d6;
    color: #fff;
    box-shadow: 0 2px 5px rgb(36 87 214 / 18%);
  }
  .ds-button--primary:hover {
    border-color: #1948bf;
    background: #1948bf;
    color: #fff;
  }
  .ds-button--quiet {
    border-color: transparent;
    background: transparent;
  }
  .ds-button--quiet:hover {
    border-color: #e3e9f2;
    background: #f5f7fa;
  }
  .ds-button--danger {
    border-color: #efc6ca;
    background: #fff;
    color: #ad2635;
  }
  .ds-button--sm {
    min-height: 32px;
    padding-inline: 10px;
    font-size: 12px;
  }
  .ds-button:disabled {
    cursor: not-allowed;
    opacity: 0.55;
  }
</style>
