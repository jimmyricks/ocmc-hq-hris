<script lang="ts">
  import { Switch as BitsSwitch } from "bits-ui";
  import type { SwitchRootProps } from "bits-ui";
  import { cn } from "$lib/utils.js";

  let {
    checked = $bindable(false),
    onCheckedChange,
    class: className,
    ...rest
  }: Omit<
    SwitchRootProps,
    "checked" | "children" | "class" | "onCheckedChange"
  > & {
    checked?: boolean;
    onCheckedChange?: (value: boolean) => void;
    class?: string;
  } = $props();
</script>

<BitsSwitch.Root
  {...rest}
  bind:checked
  {onCheckedChange}
  class={cn("hq-switch", className)}
>
  <span class="hq-switch__thumb"></span>
</BitsSwitch.Root>

<style>
  :global(.hq-switch) {
    position: relative;
    display: inline-flex;
    width: 38px;
    height: 22px;
    flex: none;
    align-items: center;
    border: 1px solid #c9d2df;
    border-radius: 999px;
    background: #e7edf4;
    padding: 2px;
    cursor: pointer;
    transition:
      background 140ms ease,
      border-color 140ms ease;
  }
  :global(.hq-switch__thumb) {
    width: 16px;
    height: 16px;
    border-radius: 50%;
    background: #fff;
    box-shadow: 0 1px 3px rgb(32 42 56 / 22%);
    transition: transform 140ms ease;
  }
  :global(.hq-switch[data-state="checked"]) {
    border-color: var(--primary);
    background: var(--primary);
  }
  :global(.hq-switch[data-state="checked"] .hq-switch__thumb) {
    transform: translateX(16px);
  }
  :global(.hq-switch:disabled) {
    cursor: not-allowed;
    opacity: 0.55;
  }
</style>
