<script lang="ts">
  import { getContext, type Snippet } from "svelte";
  import type { HTMLAttributes } from "svelte/elements";
  import { SELECT_CONTEXT, type SelectContext, type SelectOption } from "./context.js";

  let {
    value,
    label = String(value),
    disabled = false,
    children,
    ...rest
  }: HTMLAttributes<HTMLElement> & {
    value: string;
    label?: string;
    disabled?: boolean;
    children?: Snippet;
  } = $props();
  const select = getContext<SelectContext>(SELECT_CONTEXT);
  const option: SelectOption = {
    get value() { return value; },
    get label() { return label; },
    get disabled() { return disabled; },
    get children() { return children; },
  } as SelectOption;

  $effect(() => select.register(option));
</script>
