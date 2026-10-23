<script lang="ts">
  import { onMount } from "svelte";
  import { goto } from "$app/navigation";
  import { getToken } from "$lib/auth";
  import { useAppState } from "$lib/app-state.svelte.js";

  let { children } = $props();
  const appState = useAppState();
  let allowed = $state(false);
  let checked = $state(false);

  onMount(async () => {
    if (!getToken()) {
      await goto("/login");
      return;
    }
    const boot = await appState.ensureBoot();
    const hasAdminRole = Boolean(
      boot?.user?.is_superuser ||
        boot?.user?.roles?.some((role) =>
          ["Administrator", "SystemManager"].includes(role),
        ),
    );
    allowed = Boolean(
      boot?.workspace_context?.capabilities?.is_system_admin ?? hasAdminRole,
    );
    checked = true;
    if (!allowed) await goto("/dashboard");
  });
</script>

{#if allowed}
  {@render children()}
{:else if !checked}
  <p class="py-12 text-center text-sm text-base-content/60" role="status">
    Checking access...
  </p>
{/if}
