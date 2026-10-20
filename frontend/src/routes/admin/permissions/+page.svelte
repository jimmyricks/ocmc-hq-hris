<script lang="ts">
  import { onMount } from "svelte";
  import * as Table from "$lib/components/ui/table/index.js";
  import { Button } from "$lib/components/ui/button/index.js";
  import { Badge } from "$lib/components/ui/badge/index.js";
  import { Spinner } from "$lib/components/ui/spinner/index.js";
  import * as Empty from "$lib/components/ui/empty/index.js";
  import * as Select from "$lib/components/ui/select/index.js";
  import { Checkbox } from "$lib/components/ui/checkbox/index.js";
  import { apiJSON } from "$lib/api/index.js";
  import { toast } from "svelte-sonner";
  import ShieldIcon from "@lucide/svelte/icons/shield";

  interface Permission {
    id: string;
    name: string;
    description: string;
  }

  interface Role {
    id: string;
    name: string;
    permissions: Array<{ id: string; name: string }>;
  }

  let permissions = $state<Permission[]>([]);
  let roles = $state<Role[]>([]);
  let loading = $state(true);
  let selectedRoleId = $state<string>("");
  let saving = $state(false);

  let selectedRole = $derived(
    roles.find((r) => r.id === selectedRoleId) ?? null,
  );

  // Map of permission IDs that the selected role has
  let rolePermissionIds = $state<Set<string>>(new Set());

  function syncRolePermissions() {
    rolePermissionIds = new Set(
      selectedRole?.permissions.map((p) => p.id) ?? [],
    );
  }

  $effect(() => {
    // Re-sync when the selected role changes
    selectedRole;
    syncRolePermissions();
  });

  async function loadData() {
    loading = true;
    try {
      const [permData, roleData] = await Promise.all([
        apiJSON("/api/admin/permissions"),
        apiJSON("/api/admin/roles"),
      ]);
      permissions = permData.data || [];
      roles = roleData.data || [];
      if (roles.length > 0 && !selectedRoleId) {
        selectedRoleId = roles[0].id;
      }
      syncRolePermissions();
    } catch (error) {
      console.error("Failed to load data:", error);
    } finally {
      loading = false;
    }
  }

  function togglePermission(permId: string, checked: boolean) {
    const next = new Set(rolePermissionIds);
    if (checked) {
      next.add(permId);
    } else {
      next.delete(permId);
    }
    rolePermissionIds = next;
  }

  async function savePermissions() {
    if (!selectedRole) return;
    saving = true;
    try {
      await apiJSON(`/api/admin/roles/${selectedRole.id}/permissions`, {
        method: "PUT",
        body: JSON.stringify({
          permission_ids: Array.from(rolePermissionIds),
        }),
      });
      toast.success("Permissions updated");
      await loadData();
    } catch (error) {
      console.error("Failed to save permissions:", error);
      toast.error("Failed to save permissions");
    } finally {
      saving = false;
    }
  }

  onMount(() => {
    loadData();
  });
</script>

<div class="flex flex-col gap-6">
  <div class="flex items-center justify-between">
    <div>
      <h1 class="text-2xl font-bold tracking-tight">Permissions</h1>
      <p class="text-sm text-muted-foreground">
        Manage role-based access control
      </p>
    </div>
    <Button onclick={savePermissions} disabled={saving || !selectedRole}>
      {saving ? "Saving..." : "Save Changes"}
    </Button>
  </div>

  {#if loading}
    <div class="flex items-center justify-center py-12">
      <Spinner class="size-8" />
    </div>
  {:else}
    <div class="flex flex-col gap-4">
      <div class="flex items-center gap-3">
        <span class="text-sm font-medium">Role:</span>
        <Select.Root
          type="single"
          value={selectedRoleId}
          onValueChange={(v) => (selectedRoleId = v ?? "")}
        >
          <Select.Trigger class="w-48">
            {selectedRole?.name ?? "Select role..."}
          </Select.Trigger>
          <Select.Content>
            {#each roles as role (role.id)}
              <Select.Item value={role.id} label={role.name}>
                {role.name}
              </Select.Item>
            {/each}
          </Select.Content>
        </Select.Root>
      </div>

      <div class="border rounded-xl">
        {#if permissions.length > 0}
          <Table.Root>
            <Table.Header>
              <Table.Row>
                <Table.Head class="w-12"></Table.Head>
                <Table.Head>Permission</Table.Head>
                <Table.Head>Description</Table.Head>
              </Table.Row>
            </Table.Header>
            <Table.Body>
              {#each permissions as perm (perm.id)}
                <Table.Row>
                  <Table.Cell>
                    <Checkbox
                      checked={rolePermissionIds.has(perm.id)}
                      onCheckedChange={(v) =>
                        togglePermission(perm.id, v === true)}
                    />
                  </Table.Cell>
                  <Table.Cell class="font-mono text-sm">{perm.name}</Table.Cell>
                  <Table.Cell class="text-sm text-muted-foreground"
                    >{perm.description}</Table.Cell
                  >
                </Table.Row>
              {/each}
            </Table.Body>
          </Table.Root>
        {:else}
          <Empty.Root class="py-16">
            <Empty.Media variant="icon">
              <ShieldIcon />
            </Empty.Media>
            <Empty.Header>
              <Empty.Title>No permissions defined</Empty.Title>
              <Empty.Description>
                Permissions will appear here once defined in the backend.
              </Empty.Description>
            </Empty.Header>
          </Empty.Root>
        {/if}
      </div>
    </div>
  {/if}
</div>
