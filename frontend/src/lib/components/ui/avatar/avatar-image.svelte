<script lang="ts">
  import type { HTMLImgAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";
  let { class: className, ...rest }: HTMLImgAttributes = $props();
</script>

<img class={cn("size-full rounded-full object-cover", className)} {...rest} />
