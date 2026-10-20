<script lang="ts">
  import type { Snippet } from "svelte";
  let {
    errors = [],
    children,
  }: {
    errors?: Array<{ message?: string }>;
    children?: Snippet;
  } = $props();
  const messages = $derived(errors.map((error) => error.message).filter(Boolean));
</script>

{#if children}
  {@render children()}
{:else}
  {#each messages as message (message)}
    <p class="hq-field__error">{message}</p>
  {/each}
{/if}

<style>
  .hq-field__error { margin: 0; color: #ad2635; font-size: 12px; }
</style>
