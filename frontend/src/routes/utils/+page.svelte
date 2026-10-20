<script lang="ts">
  import { onMount } from "svelte";
  import { goto } from "$app/navigation";

  onMount(() => {
    goto("/utils/links");
  });
</script>

<div class="flex h-screen items-center justify-center">
  <p class="text-muted-foreground">Loading...</p>
</div>
