<script lang="ts">
  import { getContext, type Snippet } from "svelte";
  import type { HTMLAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";
  import { SELECT_CONTEXT, type SelectContext } from "./context.js";
  let {
    children,
    class: className,
    align = "start",
    portal = false,
    ...rest
  }: HTMLAttributes<HTMLElement> & {
    children?: Snippet;
    align?: "start" | "end" | "center";
    class?: string;
    portal?: boolean;
  } = $props();
  const select = getContext<SelectContext>(SELECT_CONTEXT);
  let contentEl = $state<HTMLElement | null>(null);

  $effect(() => {
    select.contentEl = contentEl;
    return () => {
      if (select.contentEl === contentEl) select.contentEl = null;
    };
  });

  function attachToBody(node: HTMLElement) {
    if (!portal) return;
    document.body.appendChild(node);
    return () => {
      node.remove();
    };
  }

  $effect(() => {
    const anchor = select.anchor;
    const el = contentEl;
    if (!portal || !select.open || !anchor || !el) return;

    const position = () => {
      const rect = anchor.getBoundingClientRect();
      el.style.left = `${align === "end" ? rect.right - el.offsetWidth : rect.left}px`;
      el.style.width = align === "end" ? "" : `${rect.width}px`;
      const spaceBelow = window.innerHeight - rect.bottom;
      const needed = Math.min(el.offsetHeight, 288) + 8;
      if (spaceBelow < needed && rect.top > spaceBelow) {
        el.style.top = "";
        el.style.bottom = `${window.innerHeight - rect.top + 4}px`;
        el.style.maxHeight = `${Math.max(120, rect.top - 12)}px`;
      } else {
        el.style.top = `${rect.bottom + 4}px`;
        el.style.bottom = "";
        el.style.maxHeight = `${Math.max(120, spaceBelow - 12)}px`;
      }
    };
    position();
    window.addEventListener("scroll", position, true);
    window.addEventListener("resize", position);
    return () => {
      window.removeEventListener("scroll", position, true);
      window.removeEventListener("resize", position);
    };
  });
</script>

<div
  bind:this={contentEl}
  {@attach attachToBody}
  class={cn(
    "dropdown-content z-50 max-h-72 overflow-y-auto rounded-lg border border-base-300 bg-base-100 p-1 shadow-md",
    portal ? "fixed" : "absolute top-full mt-1 w-full",
    !portal && align === "end" && "end-0",
    className,
  )}
  hidden={!select.open}
  {...rest}
>
  <ul class="menu m-0 w-full gap-0.5 p-0" role="listbox">
    {#each select.options as option (option.value)}
      <li>
        <button
          type="button"
          role="option"
          aria-selected={select.value === option.value}
          class:menu-active={select.value === option.value}
          class="w-full justify-start text-left"
          disabled={option.disabled}
          onclick={() => select.select(option)}
        >
          {#if option.children}
            {@render option.children()}
          {:else}
            {option.label}
          {/if}
        </button>
      </li>
    {/each}
  </ul>
  <div class="hidden" aria-hidden="true">
    {@render children?.()}
  </div>
</div>
