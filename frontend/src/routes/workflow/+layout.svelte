<script lang="ts">
  import SystemAdminGuard from "$lib/components/system-admin-guard.svelte";

  let { children } = $props();
</script>

<SystemAdminGuard>
  {@render children()}
</SystemAdminGuard>
