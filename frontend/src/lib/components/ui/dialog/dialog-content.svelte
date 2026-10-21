<script lang="ts">
  import { getContext, type Snippet } from "svelte";
  import type { HTMLDialogAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";
  import { DIALOG_CONTEXT, type DialogContext } from "./context.js";

  let {
    children,
    class: className,
    position = "middle",
    ...rest
  }: Omit<HTMLDialogAttributes, "class" | "open"> & {
    children?: Snippet;
    class?: string;
    position?: "middle" | "top" | "bottom" | "start" | "end";
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
  class={cn("modal", `modal-${position}`)}
  onclose={() => dialogState.setOpen(false)}
  onclick={(event) => {
    if (event.target === element) dialogState.setOpen(false);
  }}
  {...rest}
>
  <div
    class={cn(
      "modal-box relative max-w-lg border border-base-300 bg-base-100 p-5 text-base-content shadow-xl",
      className,
    )}
  >
    {@render children?.()}
  </div>
</dialog>
