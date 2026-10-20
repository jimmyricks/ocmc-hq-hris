<script lang="ts">
  import type { Snippet } from "svelte";
  import type { HTMLAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";
  let { children, class: className, ...rest }: HTMLAttributes<HTMLElement> & { children?: Snippet; class?: string } = $props();
</script>
<footer class={cn("hq-dialog__footer", className)} {...rest}>{@render children?.()}</footer>
<style>.hq-dialog__footer{display:flex;justify-content:flex-end;gap:8px;margin-top:18px;}</style>
