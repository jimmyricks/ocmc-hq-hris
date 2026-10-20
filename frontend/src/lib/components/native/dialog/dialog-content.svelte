<script lang="ts">
  import { getContext, type Snippet } from "svelte";
  import type { HTMLDialogAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";
  import { DIALOG_CONTEXT, type DialogContext } from "./context.js";

  let {
    children,
    class: className,
    ...rest
  }: Omit<HTMLDialogAttributes, "class" | "open"> & {
    children?: Snippet;
    class?: string;
  } = $props();
  const dialogState = getContext<DialogContext>(DIALOG_CONTEXT);
  let element: HTMLDialogElement;

  $effect(() => {
    if (!element) return;
    if (dialogState.open && !element.open) element.showModal();
    if (!dialogState.open && element.open) element.close();
  });
</script>

<dialog
  bind:this={element}
  class={cn("hq-dialog", className)}
  onclose={() => dialogState.setOpen(false)}
  onclick={(event) => {
    if (event.target === element) dialogState.setOpen(false);
  }}
  {...rest}
>
  {@render children?.()}
</dialog>

<style>
  .hq-dialog {
    position: fixed;
    width: min(calc(100vw - 32px), 520px);
    max-height: min(86vh, 860px);
    margin: auto;
    overflow-y: auto;
    border: 1px solid var(--border);
    border-radius: 12px;
    background: var(--card);
    color: var(--card-foreground);
    padding: 20px;
    box-shadow: 0 18px 55px rgb(20 29 41 / 18%);
  }
  .hq-dialog::backdrop {
    background: rgb(24 32 45 / 38%);
  }
</style>
