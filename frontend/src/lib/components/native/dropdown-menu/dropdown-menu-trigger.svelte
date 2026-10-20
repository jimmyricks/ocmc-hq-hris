<script lang="ts">
  import { getContext, type Snippet } from "svelte";
  import type { HTMLAttributes } from "svelte/elements";
  import { DROPDOWN_MENU_CONTEXT, type DropdownMenuContext } from "./context.js";

  let {
    children,
    child,
    class: className,
    ...rest
  }: HTMLAttributes<HTMLElement> & {
    children?: Snippet;
    child?: Snippet<[{ props: Record<string, unknown> }]>;
    class?: string;
  } = $props();
  const menu = getContext<DropdownMenuContext>(DROPDOWN_MENU_CONTEXT);
  const triggerProps = $derived({
    ...rest,
    class: className,
    "aria-expanded": menu.open,
    "aria-haspopup": "menu",
    onclick: () => menu.toggle(),
  });
</script>

{#if child}
  {@render child({ props: triggerProps })}
{:else}
  <span
    class="hq-menu__trigger {className ?? ''}"
    role="button"
    tabindex="0"
    aria-expanded={menu.open}
    aria-haspopup="menu"
    onclick={() => menu.toggle()}
    onkeydown={(event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); menu.toggle(); } }}
    {...rest}
  >{@render children?.()}</span>
{/if}

<style>.hq-menu__trigger{display:inline-flex;}</style>
