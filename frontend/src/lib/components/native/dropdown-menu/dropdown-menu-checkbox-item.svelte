<script lang="ts">
  import type { Snippet } from "svelte";
  import type { HTMLLabelAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";
  let { children, checked = $bindable(false), onCheckedChange, class: className, ...rest }: HTMLLabelAttributes & { children?: Snippet; checked?: boolean; onCheckedChange?: (checked: boolean) => void; class?: string } = $props();
</script>
<label class={cn("hq-menu__checkbox", className)} {...rest}>
  <input type="checkbox" bind:checked onchange={(event) => onCheckedChange?.(event.currentTarget.checked)} />
  <span>{@render children?.()}</span>
</label>
<style>
  .hq-menu__checkbox{display:flex;align-items:center;gap:8px;border-radius:6px;padding:8px 9px;font-size:12px;font-weight:600;cursor:pointer;}
  .hq-menu__checkbox:hover{background:var(--muted);}
  .hq-menu__checkbox input{width:15px;height:15px;accent-color:var(--primary);}
</style>
