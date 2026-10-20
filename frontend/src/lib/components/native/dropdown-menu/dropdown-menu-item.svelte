<script lang="ts">
  import { getContext, type Snippet } from "svelte";
  import type { HTMLButtonAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";
  import {
    DROPDOWN_MENU_CONTEXT,
    type DropdownMenuContext,
  } from "./context.js";
  let {
    children,
    variant = "default",
    class: className,
    ...rest
  }: Omit<HTMLButtonAttributes, "class"> & {
    children?: Snippet;
    variant?: "default" | "destructive";
    class?: string;
  } = $props();
  const menu = getContext<DropdownMenuContext>(DROPDOWN_MENU_CONTEXT);
</script>

<button
  type="button"
  role="menuitem"
  class={cn(
    "hq-menu__item",
    variant === "destructive" && "hq-menu__item--destructive",
    className,
  )}
  {...rest}
  onclick={(event) => {
    rest.onclick?.(event);
    if (!event.defaultPrevented) menu.setOpen(false);
  }}
>
  {@render children?.()}
</button>

<style>
  .hq-menu__item {
    display: flex;
    width: 100%;
    align-items: center;
    gap: 8px;
    border: 0;
    border-radius: 6px;
    background: transparent;
    padding: 8px 9px;
    color: inherit;
    font-size: 12px;
    font-weight: 600;
    text-align: left;
    cursor: pointer;
  }
  .hq-menu__item:hover {
    background: var(--muted);
  }
  .hq-menu__item--destructive {
    color: #ad2635;
  }
  .hq-menu__item--destructive:hover {
    background: #fff4f5;
  }
  .hq-menu__item:disabled {
    cursor: not-allowed;
    opacity: 0.55;
  }
</style>
