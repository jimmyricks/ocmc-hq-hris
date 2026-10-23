<script lang="ts">
  import { getContext, type Snippet } from "svelte";
  import type { HTMLAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";
  import {
    DROPDOWN_MENU_CONTEXT,
    type DropdownMenuContext,
  } from "./context.js";
  let {
    children,
    align = "start",
    side = "bottom",
    class: className,
    ...rest
  }: HTMLAttributes<HTMLElement> & {
    children?: Snippet;
    align?: "start" | "center" | "end";
    side?: "bottom" | "top";
    class?: string;
  } = $props();
  const menu = getContext<DropdownMenuContext>(DROPDOWN_MENU_CONTEXT);
</script>

{#if menu.open}
  <div
    role="menu"
    class={cn(
      "dropdown-content absolute z-50 grid min-w-45 gap-0.5 rounded-lg border border-base-300 bg-base-100 p-1 shadow-md",
      side === "top" ? "bottom-[calc(100%+6px)]" : "top-[calc(100%+6px)]",
      `dropdown-content--${align}`,
      className,
    )}
    {...rest}
  >
    {@render children?.()}
  </div>
{/if}

<style>
  .dropdown-content--start {
    left: 0;
  }
  .dropdown-content--center {
    left: 50%;
    transform: translateX(-50%);
  }
  .dropdown-content--end {
    right: 0;
  }
</style>
