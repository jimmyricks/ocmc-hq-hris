<script lang="ts">
  import type { HTMLImgAttributes } from "svelte/elements";
  import { cn } from "$lib/utils.js";
  let { class: className, ...rest }: HTMLImgAttributes = $props();
</script>

<img class={cn("hq-avatar__image", className)} {...rest} />

<style>
  .hq-avatar__image { width: 100%; height: 100%; object-fit: cover; }
</style>
