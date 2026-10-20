<script lang="ts">
  import type { Snippet } from "svelte";

  let {
    children,
    class: className = "",
    as = "section",
  }: {
    children?: Snippet;
    class?: string;
    as?: "section" | "div" | "article";
  } = $props();
</script>

{#if as === "article"}
  <article class="ds-panel {className}">{@render children?.()}</article>
{:else if as === "div"}
  <div class="ds-panel {className}">{@render children?.()}</div>
{:else}
  <section class="ds-panel {className}">{@render children?.()}</section>
{/if}

<style>
  .ds-panel {
    border: 1px solid #dbe1e9;
    border-radius: 10px;
    background: #fff;
    box-shadow: 0 1px 2px rgb(32 42 56 / 3%);
  }
</style>
