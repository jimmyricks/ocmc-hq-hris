<script lang="ts">
  import type { Snippet } from "svelte";
  import type { HTMLButtonAttributes } from "svelte/elements";
  let {
    children,
    size = "sm",
    variant = "default",
    class: className = "",
    ...rest
  }: Omit<HTMLButtonAttributes, "class"> & {
    children?: Snippet;
    size?: string;
    variant?: string;
    class?: string;
  } = $props();
</script>

<button
  type="button"
  class="hq-input-group__button {size.includes('icon')
    ? 'hq-input-group__button--icon'
    : ''} {className}"
  {...rest}>{@render children?.()}</button
>

<style>
  .hq-input-group__button {
    display: inline-flex;
    min-height: 30px;
    align-items: center;
    justify-content: center;
    border: 0;
    border-radius: 6px;
    background: var(--primary);
    padding: 0 9px;
    color: var(--primary-foreground);
    font-size: 12px;
    font-weight: 650;
    cursor: pointer;
  }
  .hq-input-group__button--icon {
    width: 30px;
    padding: 0;
  }
  .hq-input-group__button:disabled {
    cursor: not-allowed;
    opacity: 0.55;
  }
</style>
