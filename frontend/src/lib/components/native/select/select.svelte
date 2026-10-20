<script lang="ts">
  import { setContext, type Snippet } from "svelte";
  import type { HTMLAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";
  import { SELECT_CONTEXT, type SelectContext, type SelectOption } from "./context.js";

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
  let options = $state<SelectOption[]>([]);
  let root: HTMLElement;

  const context: SelectContext = {
    get value() { return value; },
    get open() { return open; },
    get disabled() { return disabled; },
    get options() { return options; },
    setOpen(next) {
      open = next;
      onOpenChange?.(next);
    },
    toggle() { if (!disabled) this.setOpen(!open); },
    select(option) {
      if (option.disabled) return;
      value = option.value;
      onValueChange?.(option.value);
      this.setOpen(false);
    },
    register(option) {
      options = [...options, option];
      return () => {
        options = options.filter((entry) => entry !== option);
      };
    },
  };
  setContext(SELECT_CONTEXT, context);

  $effect(() => {
    const closeOnOutside = (event: MouseEvent) => {
      if (open && root && !root.contains(event.target as Node)) context.setOpen(false);
    };
    document.addEventListener("mousedown", closeOnOutside);
    return () => document.removeEventListener("mousedown", closeOnOutside);
  });
</script>

<div bind:this={root} class={cn("hq-select", className)} {...rest}>{@render children?.()}</div>

<style>.hq-select{position:relative;display:block;min-width:0;}</style>
