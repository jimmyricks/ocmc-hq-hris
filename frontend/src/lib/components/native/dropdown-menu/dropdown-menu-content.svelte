<script lang="ts">
  import { getContext, type Snippet } from "svelte";
  import type { HTMLAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";
  import { DROPDOWN_MENU_CONTEXT, type DropdownMenuContext } from "./context.js";
  let { children, align = "start", side = "bottom", class: className, ...rest }: HTMLAttributes<HTMLElement> & { children?: Snippet; align?: "start" | "center" | "end"; side?: string; class?: string } = $props();
  const menu = getContext<DropdownMenuContext>(DROPDOWN_MENU_CONTEXT);
</script>

{#if menu.open}
  <div role="menu" class={cn("hq-menu__content", `hq-menu__content--${align}`, className)} {...rest}>
    {@render children?.()}
  </div>
{/if}

<style>
  .hq-menu__content{position:absolute;top:calc(100% + 6px);z-index:60;display:grid;min-width:180px;gap:2px;border:1px solid var(--border);border-radius:9px;background:var(--card);padding:4px;box-shadow:0 10px 30px rgb(20 29 41 / 12%);}
  .hq-menu__content--start{left:0;}
  .hq-menu__content--center{left:50%;transform:translateX(-50%);}
  .hq-menu__content--end{right:0;}
</style>
