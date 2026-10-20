<script lang="ts">
  import { Checkbox as BitsCheckbox } from "bits-ui";
  import type { CheckboxRootProps } from "bits-ui";
  import { cn } from "$lib/utils.js";

  let {
    checked = $bindable(false),
    onCheckedChange,
    required,
    name,
    value,
    class: className,
    ...rest
  }: Omit<
    CheckboxRootProps,
    "class" | "checked" | "children" | "onCheckedChange"
  > & {
    checked?: boolean;
    onCheckedChange?: (value: boolean) => void;
    class?: string;
  } = $props();
</script>

<BitsCheckbox.Root
  {...rest}
  bind:checked
  {onCheckedChange}
  {required}
  {name}
  {value}
  class={cn("hq-checkbox", className)}
/>

<style>
  :global(.hq-checkbox) {
    display: inline-flex;
    width: 17px;
    height: 17px;
    flex: none;
    align-items: center;
    justify-content: center;
    border: 1px solid var(--border);
    border-radius: 4px;
    background: var(--card);
    color: var(--primary-foreground);
    cursor: pointer;
    padding: 0;
  }
  :global(.hq-checkbox[data-state="checked"]) {
    border-color: var(--primary);
    background: var(--primary);
  }
  :global(.hq-checkbox[data-state="checked"]::after) {
    width: 8px;
    height: 4px;
    border-bottom: 2px solid currentColor;
    border-left: 2px solid currentColor;
    content: "";
    transform: translateY(-1px) rotate(-45deg);
  }
  :global(.hq-checkbox:disabled) {
    cursor: not-allowed;
    opacity: 0.55;
  }
</style>
