<script lang="ts">
  import type { HTMLInputAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";

  let {
    checked = $bindable(false),
    onCheckedChange,
    class: className,
    ...rest
  }: Omit<HTMLInputAttributes, "class" | "checked" | "type"> & {
    checked?: boolean;
    onCheckedChange?: (value: boolean) => void;
    class?: string;
  } = $props();
</script>

<input
  {...rest}
  type="checkbox"
  class={cn("checkbox checkbox-primary", className)}
  bind:checked
  onchange={(event) => onCheckedChange?.(event.currentTarget.checked)}
/>
