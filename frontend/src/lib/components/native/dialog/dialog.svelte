<script lang="ts">
  import { setContext, type Snippet } from "svelte";
  import { DIALOG_CONTEXT, type DialogContext } from "./context.js";

  let {
    open = $bindable(false),
    onOpenChange,
    children,
  }: {
    open?: boolean;
    onOpenChange?: (open: boolean) => void;
    children?: Snippet;
  } = $props();

  const context: DialogContext = {
    get open() { return open; },
    setOpen(next) {
      open = next;
      onOpenChange?.(next);
    },
  };
  setContext(DIALOG_CONTEXT, context);
</script>

{@render children?.()}
