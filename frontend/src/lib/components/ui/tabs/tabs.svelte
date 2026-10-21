<script lang="ts">
  import { setContext, type Snippet } from "svelte";
  import type { HTMLAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";
  import { TABS_CONTEXT, type TabsContext } from "./context.js";

  let {
    value = $bindable(""),
    onValueChange,
    children,
    class: className,
    ...rest
  }: HTMLAttributes<HTMLElement> & {
    value?: string;
    onValueChange?: (value: string) => void;
    children?: Snippet;
    class?: string;
  } = $props();

  const context: TabsContext = {
    get value() {
      return value;
    },
    setValue(next) {
      value = next;
      onValueChange?.(next);
    },
  };
  setContext(TABS_CONTEXT, context);
</script>

<div class={cn("flex min-w-0 flex-col", className)} {...rest}>
  {@render children?.()}
</div>
