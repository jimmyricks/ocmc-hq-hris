<script lang="ts">
  import { getContext, type Snippet } from "svelte";
  import type { HTMLButtonAttributes } from "svelte/elements";
  import { DIALOG_CONTEXT, type DialogContext } from "./context.js";
  let { children, ...rest }: Omit<HTMLButtonAttributes, "type"> & { children?: Snippet } = $props();
  const dialogState = getContext<DialogContext>(DIALOG_CONTEXT);
</script>
<button type="button" {...rest} onclick={(event) => { rest.onclick?.(event); if (!event.defaultPrevented) dialogState.setOpen(false); }}>
  {@render children?.()}
</button>
