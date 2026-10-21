<script lang="ts">
  import type { Snippet } from "svelte";
  import type { HTMLLabelAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";
  let {
    children,
    checked = $bindable(false),
    onCheckedChange,
    class: className,
    ...rest
  }: HTMLLabelAttributes & {
    children?: Snippet;
    checked?: boolean;
    onCheckedChange?: (checked: boolean) => void;
    class?: string;
  } = $props();
</script>

<label
  class={cn(
    "flex cursor-pointer items-center gap-2 rounded-md px-2 py-1.5 text-sm font-medium hover:bg-base-200",
    className,
  )}
  {...rest}
>
  <input
    class="checkbox checkbox-primary"
    type="checkbox"
    bind:checked
    onchange={(event) => onCheckedChange?.(event.currentTarget.checked)}
  />
  <span>{@render children?.()}</span>
</label>
