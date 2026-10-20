<script lang="ts">
  import { getContext, type Snippet } from "svelte";
  import type { HTMLButtonAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";
  import { SELECT_CONTEXT, type SelectContext } from "./context.js";
  let { children, class: className, ...rest }: Omit<HTMLButtonAttributes, "class"> & { children?: Snippet; class?: string } = $props();
  const select = getContext<SelectContext>(SELECT_CONTEXT);
</script>

<button
  type="button"
  role="combobox"
  aria-expanded={select.open}
  aria-haspopup="listbox"
  class={cn("hq-select__trigger", className)}
  {...rest}
  disabled={select.disabled || rest.disabled}
  onclick={(event) => { rest.onclick?.(event); if (!event.defaultPrevented) select.toggle(); }}
>
  {@render children?.()}
</button>

<style>
  .hq-select__trigger{display:flex;width:100%;min-height:38px;align-items:center;justify-content:space-between;gap:8px;border:1px solid var(--input);border-radius:8px;background:#fff;padding:0 11px;color:var(--foreground);font-size:13px;text-align:left;cursor:pointer;}
  .hq-select__trigger:hover{border-color:#aeb9c9;}
  .hq-select__trigger[aria-expanded="true"]{border-color:var(--primary);box-shadow:0 0 0 3px rgb(120 149 232 / 22%);}
  .hq-select__trigger:disabled{background:var(--muted);color:var(--muted-foreground);cursor:not-allowed;}
</style>
