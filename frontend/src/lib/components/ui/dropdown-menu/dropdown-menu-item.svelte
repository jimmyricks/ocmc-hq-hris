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
    "flex w-full items-center gap-2 rounded-md border-0 bg-transparent px-2 py-1.5 text-left text-sm font-medium text-base-content hover:bg-base-200 disabled:cursor-not-allowed disabled:opacity-50",
    variant === "destructive" && "text-error hover:bg-error/10",
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
