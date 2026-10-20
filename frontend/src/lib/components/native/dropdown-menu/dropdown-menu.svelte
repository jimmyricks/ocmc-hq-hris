<script lang="ts">
  import { setContext, type Snippet } from "svelte";
  import type { HTMLAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";
  import { DROPDOWN_MENU_CONTEXT, type DropdownMenuContext } from "./context.js";

  let {
    open = $bindable(false),
    onOpenChange,
    children,
    class: className,
    ...rest
  }: HTMLAttributes<HTMLElement> & {
    open?: boolean;
    onOpenChange?: (open: boolean) => void;
    children?: Snippet;
    class?: string;
  } = $props();

  let root: HTMLElement;
  const context: DropdownMenuContext = {
    get open() { return open; },
    setOpen(next) {
      open = next;
      onOpenChange?.(next);
    },
    toggle() { this.setOpen(!open); },
  };
  setContext(DROPDOWN_MENU_CONTEXT, context);

  $effect(() => {
    const closeOnOutside = (event: MouseEvent) => {
      if (open && root && !root.contains(event.target as Node)) context.setOpen(false);
    };
    document.addEventListener("mousedown", closeOnOutside);
    return () => document.removeEventListener("mousedown", closeOnOutside);
  });
</script>

<div bind:this={root} class={cn("hq-menu", className)} {...rest}>{@render children?.()}</div>

<style>.hq-menu{position:relative;display:inline-flex;}</style>
