<script lang="ts">
  import type { Snippet } from "svelte";

  let {
    open = $bindable(false),
    children,
    class: className = "",
    labelledBy,
  }: {
    open?: boolean;
    children?: Snippet;
    class?: string;
    labelledBy?: string;
  } = $props();

  let dialog: HTMLDialogElement;

  $effect(() => {
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  });

  function syncOpen() {
    open = dialog.open;
  }
</script>

<dialog
  bind:this={dialog}
  class="ds-modal {className}"
  aria-labelledby={labelledBy}
  onclose={syncOpen}
  onclick={(event) => {
    if (event.target === dialog) dialog.close();
  }}
>
  {@render children?.()}
</dialog>

<style>
  .ds-modal {
    width: min(520px, calc(100vw - 28px));
    max-width: none;
    max-height: min(88vh, 780px);
    overflow: auto;
    border: 1px solid #dbe1e9;
    border-radius: 12px;
    background: #fff;
    padding: 0;
    color: #202a38;
    box-shadow: 0 24px 80px rgb(24 36 54 / 22%);
  }
  .ds-modal::backdrop {
    background: rgb(25 36 52 / 42%);
    backdrop-filter: blur(2px);
  }
</style>
