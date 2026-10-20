<script lang="ts">
  import { getContext, type Snippet } from "svelte";
  import type { HTMLAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";
  import { SELECT_CONTEXT, type SelectContext } from "./context.js";
  let { children, class: className, align = "start", ...rest }: HTMLAttributes<HTMLElement> & { children?: Snippet; align?: "start" | "end" | "center"; class?: string } = $props();
  const select = getContext<SelectContext>(SELECT_CONTEXT);
</script>

<div class={cn("hq-select__content", `hq-select__content--${align}`, className)} hidden={!select.open} {...rest}>
  <div role="listbox" class="hq-select__list">
    {#each select.options as option (option.value)}
      <button
        type="button"
        role="option"
        aria-selected={select.value === option.value}
        class="hq-select__option"
        disabled={option.disabled}
        onclick={() => select.select(option)}
      >
        {#if option.children}
          {@render option.children()}
        {:else}
          {option.label}
        {/if}
      </button>
    {/each}
  </div>
  <div class="hq-select__registrations" aria-hidden="true">{@render children?.()}</div>
</div>

<style>
  .hq-select__content{position:absolute;top:calc(100% + 6px);left:0;right:auto;z-index:70;width:max-content;min-width:100%;max-width:min(420px,calc(100vw - 24px));border:1px solid var(--border);border-radius:9px;background:var(--card);box-shadow:0 10px 30px rgb(20 29 41 / 12%);}
  .hq-select__content--end{right:0;}
  .hq-select__list{display:grid;max-height:280px;overflow:auto;padding:4px;gap:2px;}
  .hq-select__option{display:flex;width:100%;align-items:center;gap:8px;border:0;border-radius:6px;background:transparent;padding:8px 9px;color:inherit;font-size:12px;font-weight:600;text-align:left;cursor:pointer;}
  .hq-select__option:hover{background:var(--muted);}
  .hq-select__option[aria-selected="true"]{background:#eaf0ff;color:#2457d6;}
  .hq-select__option:disabled{cursor:not-allowed;opacity:0.5;}
  .hq-select__registrations{display:none;}
</style>
