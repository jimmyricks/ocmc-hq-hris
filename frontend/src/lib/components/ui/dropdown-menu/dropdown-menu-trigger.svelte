<script lang="ts">
  import { getContext, type Snippet } from "svelte";
  import type { HTMLAttributes } from "svelte/elements";
  import {
    DROPDOWN_MENU_CONTEXT,
    type DropdownMenuContext,
  } from "./context.js";

  let {
    children,
    child,
    class: className,
    onclick,
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
  const childProps = $derived.by(() => {
    const { onclick: _onclick, ...props } = triggerProps;
    return props;
  });

  function handleTriggerClick(
    event: MouseEvent & { currentTarget: EventTarget & HTMLElement },
  ) {
    event.preventDefault();
    menu.toggle();
    onclick?.(event);
    if (!event.defaultPrevented) {
      event.preventDefault();
      menu.toggle();
    }
  }
</script>

{#if child}
  <summary
    class="dropdown-trigger inline-flex cursor-pointer list-none {className ??
      ''}"
    aria-expanded={menu.open}
    aria-haspopup="menu"
    onclick={handleTriggerClick}
    {...rest}>{@render child({ props: childProps })}</summary
  >
{:else}
  <summary
    class="dropdown-trigger inline-flex cursor-pointer list-none {className ??
      ''}"
    aria-expanded={menu.open}
    aria-haspopup="menu"
    onclick={handleTriggerClick}
    {...rest}>{@render children?.()}</summary
  >
{/if}

<style>
  .dropdown-trigger::-webkit-details-marker {
    display: none;
  }
  .dropdown-trigger::marker {
    content: "";
  }
  /* daisyUI sets pointer-events:none on a focused .dropdown's first [tabindex]
     child (meant for its focus-based dropdowns). This menu toggles via JS, so
     keep the trigger clickable or the opening click is swallowed mid-flight. */
  :global(.dropdown:focus-within) > .dropdown-trigger:first-child {
    pointer-events: auto;
  }
</style>
