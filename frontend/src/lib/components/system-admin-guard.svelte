<script lang="ts">
  import { onMount } from "svelte";
  import { goto } from "$app/navigation";
  import { getToken, getUser } from "$lib/auth";
  import { workspaceApi } from "$lib/workspaces/api";

  let { children } = $props();
  let allowed = $state(false);
  let checked = $state(false);

  onMount(async () => {
    if (!getToken()) {
      await goto("/login");
      return;
    }
    try {
      const context = await workspaceApi.getContext();
      const hasAdminRole = Boolean(
        getUser()?.is_superuser ||
          getUser()?.roles?.some((role) =>
            ["Administrator", "SystemManager"].includes(role),
          ),
      );
      allowed = context.capabilities?.is_system_admin ?? hasAdminRole;
    } catch {
      allowed = false;
    } finally {
      checked = true;
    }
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
