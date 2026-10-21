<script lang="ts">
  import type { HTMLTextareaAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";

  type Props = Omit<HTMLTextareaAttributes, "class" | "value" | "size"> & {
    value?: string;
    ref?: HTMLTextAreaElement | null;
    size?: "xs" | "sm" | "md" | "lg" | "xl";
    class?: string;
  };

  let {
    value = $bindable(""),
    ref = $bindable(null),
    size = "md",
    class: className,
    ...rest
  }: Props = $props();

  const sizeClasses: Record<string, string> = {
    xs: "textarea-xs",
    sm: "textarea-sm",
    md: "textarea-md",
    lg: "textarea-lg",
    xl: "textarea-xl",
  };
</script>

<textarea
  bind:this={ref}
  bind:value
  class={cn("textarea border-base-300 w-full", sizeClasses[size], className)}
  {...rest}></textarea>
