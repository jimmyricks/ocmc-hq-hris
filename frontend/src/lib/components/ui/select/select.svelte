<script lang="ts">
  import { setContext, untrack, type Snippet } from "svelte";
  import type { HTMLAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";
  import {
    SELECT_CONTEXT,
    type SelectContext,
    type SelectOption,
  } from "./context.js";

  let {
    value = $bindable(""),
    onValueChange,
    onOpenChange,
    type = "single",
    disabled = false,
    children,
    class: className,
    ...rest
  }: HTMLAttributes<HTMLElement> & {
    value?: string;
    onValueChange?: (value: string) => void;
    onOpenChange?: (open: boolean) => void;
    type?: string;
    disabled?: boolean;
    children?: Snippet;
    class?: string;
  } = $props();

  let open = $state(false);
  let options = $state.raw<SelectOption[]>([]);
  let root: HTMLElement;
  let contentEl = $state<HTMLElement | null>(null);

  const context: SelectContext = {
    get value() {
      return value;
    },
    get open() {
      return open;
    },
    get disabled() {
      return disabled;
    },
    get options() {
      return options;
    },
    get anchor() {
      return root;
    },
    get contentEl() {
      return contentEl;
    },
    set contentEl(node) {
      contentEl = node;
    },
    setOpen(next) {
      open = next;
      onOpenChange?.(next);
    },
    toggle() {
      if (!disabled) this.setOpen(!open);
    },
    select(option) {
      if (option.disabled) return;
      value = option.value;
      onValueChange?.(option.value);
      this.setOpen(false);
    },
    register(option) {
      options = [...untrack(() => options), option];
      return () => {
        options = untrack(() => options).filter((entry) => entry !== option);
      };
    },
  };
  setContext(SELECT_CONTEXT, context);

  $effect(() => {
    const closeOnOutside = (event: MouseEvent) => {
      const target = event.target as Node;
      if (
        open &&
        root &&
        !root.contains(target) &&
        !contentEl?.contains(target)
      )
        context.setOpen(false);
    };
    document.addEventListener("mousedown", closeOnOutside);
    return () => document.removeEventListener("mousedown", closeOnOutside);
  });
</script>

<div
  bind:this={root}
  class={cn("dropdown relative block", className)}
  {...rest}
>
  {@render children?.()}
</div>
