<script lang="ts">
  import { getContext, type Snippet } from "svelte";
  import type { HTMLButtonAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";
  import { SELECT_CONTEXT, type SelectContext } from "./context.js";
  import ChevronDownIcon from "@lucide/svelte/icons/chevron-down";
  let {
    children,
    size = "md",
    class: className,
    ...rest
  }: Omit<HTMLButtonAttributes, "class"> & {
    children?: Snippet;
    size?: "xs" | "sm" | "md" | "lg" | "xl";
    class?: string;
  } = $props();
  const select = getContext<SelectContext>(SELECT_CONTEXT);

  const sizeClasses: Record<string, string> = {
    xs: "input-xs",
    sm: "input-sm",
    md: "input-md",
    lg: "input-lg",
    xl: "input-xl",
  };
</script>

<button
  type="button"
  role="combobox"
  aria-expanded={select.open}
  aria-haspopup="listbox"
  class={cn(
    "input border-base-300 flex w-full items-center justify-between gap-2",
    "focus:outline-none focus:ring-0 focus:shadow-none focus-visible:outline-2 focus-visible:outline-primary/55 focus-visible:outline-offset-2",
    sizeClasses[size],
    className,
  )}
  {...rest}
  disabled={select.disabled || rest.disabled}
  onclick={(event) => {
    rest.onclick?.(event);
    if (!event.defaultPrevented) select.toggle();
  }}
>
  {@render children?.()}
  <ChevronDownIcon size={16} class="shrink-0 opacity-60" aria-hidden="true" />
</button>
