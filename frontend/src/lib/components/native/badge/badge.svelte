<script lang="ts">
  import type { Snippet } from "svelte";
  import type { HTMLAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";

  let {
    children,
    variant = "default",
    class: className,
    ...rest
  }: {
    children?: Snippet;
    variant?:
      | "default"
      | "secondary"
      | "destructive"
      | "outline"
      | "primary"
      | "ghost";
    class?: string;
  } & Omit<HTMLAttributes<HTMLSpanElement>, "class"> = $props();
</script>

<span class={cn("hq-badge", `hq-badge--${variant}`, className)} {...rest}>
  {@render children?.()}
</span>

<style>
  .hq-badge {
    display: inline-flex;
    min-height: 21px;
    align-items: center;
    gap: 5px;
    border: 1px solid transparent;
    border-radius: 999px;
    padding: 0 8px;
    font-size: 10px;
    font-weight: 700;
    line-height: 1;
    white-space: nowrap;
  }
  .hq-badge--default,
  .hq-badge--primary {
    border-color: var(--primary);
    background: var(--primary);
    color: var(--primary-foreground);
  }
  .hq-badge--secondary {
    border-color: #e0e6ee;
    background: var(--secondary);
    color: var(--secondary-foreground);
  }
  .hq-badge--destructive {
    border-color: #efc6ca;
    background: #fff4f5;
    color: #ad2635;
  }
  .hq-badge--outline {
    border-color: var(--border);
    background: #fff;
    color: var(--secondary-foreground);
  }
  .hq-badge--ghost {
    border-color: transparent;
    background: transparent;
    color: var(--muted-foreground);
  }
</style>
