<script lang="ts">
  import { page } from "$app/state";
  import { goto } from "$app/navigation";
  import { type Snippet } from "svelte";
  import * as Tabs from "$lib/components/native/tabs/index.js";

  let { children }: { children?: Snippet } = $props();
  let active = $derived(page.url.pathname === "/utils/qr" ? "qr" : "links");
</script>

<div class="flex flex-col gap-6">
  <h1 class="text-2xl font-semibold tracking-tight">Utils</h1>
  <Tabs.Root value={active}>
    <Tabs.List>
      <Tabs.Trigger value="links" onclick={() => goto("/utils/links")}>
        Link Shortener
      </Tabs.Trigger>
      <Tabs.Trigger value="qr" onclick={() => goto("/utils/qr")}>
        QR Generator
      </Tabs.Trigger>
    </Tabs.List>
    <div class="mt-4">
      {#if children}{@render children()}{/if}
    </div>
  </Tabs.Root>
</div>
