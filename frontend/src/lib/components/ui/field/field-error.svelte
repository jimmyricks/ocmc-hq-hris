<script lang="ts">
  import type { Snippet } from "svelte";
  let {
    errors = [],
    children,
  }: {
    errors?: Array<{ message?: string }>;
    children?: Snippet;
  } = $props();
  const messages = $derived(
    errors.map((error) => error.message).filter(Boolean),
  );
</script>

{#if children}
  {@render children()}
{:else}
  {#each messages as message (message)}
    <p class="m-0 text-xs text-error">{message}</p>
  {/each}
{/if}
