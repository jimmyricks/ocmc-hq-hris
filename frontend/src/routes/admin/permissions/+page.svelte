<script lang="ts">
  import { onMount } from "svelte";
  import { Button } from "$lib/components/ui/button/index.js";
  import { Spinner } from "$lib/components/ui/spinner/index.js";
  import * as Empty from "$lib/components/ui/empty/index.js";
  import * as Select from "$lib/components/ui/select/index.js";
  import { Checkbox } from "$lib/components/ui/checkbox/index.js";
  import { apiJSON } from "$lib/api/index.js";
  import { toast } from "$lib/notifications";
  import { useAppState } from "$lib/app-state.svelte.js";
  import Pagination from "$lib/components/pagination.svelte";
  import ShieldIcon from "@lucide/svelte/icons/shield";

  interface EntityRow {
    name: string;
    label: string;
    module: string;
    sort_order: number;
  }

  interface Role {
    id: string;
    name: string;
  }

  type PermissionFlags = {
    can_read?: boolean;
    can_create?: boolean;
    can_update?: boolean;
    can_delete?: boolean;
    can_select?: boolean;
    can_export?: boolean;
    can_import?: boolean;
    in_sidebar?: boolean;
    row_scope?: string | string[];
  };

  const appState = useAppState();
  const permissionColumns = [
    ["can_read", "Read"],
    ["can_create", "Create"],
    ["can_update", "Update"],
    ["can_delete", "Delete"],
    ["in_sidebar", "Sidebar"],
  ] as const;

  let entities = $state<EntityRow[]>([]);
  let roles = $state<Role[]>([]);
  let rolePermissions = $state<Record<string, PermissionFlags>>({});
  let selectedRoleId = $state("");
  let selectedRole = $derived(
    roles.find((role) => role.id === selectedRoleId) ?? null,
  );
  let loading = $state(true);
  let roleLoading = $state(false);
  let saving = $state(false);
  let entitiesPage = $state(appState.tablePage("admin-permissions"));
  let entitiesPageSize = $state(25);
  let entitiesTotal = $state(0);
  let roleRequest = 0;

  async function loadEntities(page = entitiesPage) {
    loading = true;
    try {
      const response = await apiJSON(
        `/api/admin/permissions/entities?page=${page}&page_size=${entitiesPageSize}`,
      );
      const data = response.data ?? {};
      const result = (data.rows ?? []) as EntityRow[];
      const total = Number(data.total ?? data.total_entities ?? result.length);
      if (!result.length && total > 0 && page > 1) {
        return loadEntities(Math.ceil(total / entitiesPageSize));
      }
      entities = result;
      entitiesTotal = total;
      entitiesPage = Number(data.page ?? page);
      appState.rememberTablePage("admin-permissions", entitiesPage);
    } catch (error) {
      console.error("Failed to load entities:", error);
      toast.error("Failed to load permissions");
    } finally {
      loading = false;
    }
  }

  async function loadRoles() {
    try {
      const response = await apiJSON("/api/admin/roles");
      roles = response.data ?? [];
      if (roles.length && !selectedRoleId) selectedRoleId = roles[0].id;
    } catch (error) {
      console.error("Failed to load roles:", error);
      toast.error("Failed to load roles");
    }
  }

  async function loadRolePermissions(roleId: string) {
    const request = ++roleRequest;
    roleLoading = true;
    try {
      const response = await apiJSON(`/api/admin/permissions/role/${roleId}`);
      if (request !== roleRequest) return;
      rolePermissions =
        (response.data?.permissions?.entities as Record<
          string,
          PermissionFlags
        >) ?? {};
    } catch (error) {
      console.error("Failed to load role permissions:", error);
      rolePermissions = {};
    } finally {
      if (request === roleRequest) roleLoading = false;
    }
  }

  function setEntitiesPage(page: number) {
    entitiesPage = page;
    appState.rememberTablePage("admin-permissions", page);
    void loadEntities(page);
  }

  function togglePermission(
    entityName: string,
    key: keyof PermissionFlags,
    checked: boolean,
  ) {
    rolePermissions = {
      ...rolePermissions,
      [entityName]: {
        ...(rolePermissions[entityName] ?? {}),
        [key]: checked,
      },
    };
  }

  async function savePermissions() {
    if (!selectedRole) return;
    saving = true;
    try {
      await apiJSON(`/api/admin/permissions/role/${selectedRole.id}`, {
        method: "PUT",
        body: JSON.stringify({
          permissions: { entities: rolePermissions },
        }),
      });
      toast.success("Permissions updated");
      await loadRolePermissions(selectedRole.id);
    } catch (error) {
      console.error("Failed to save permissions:", error);
      toast.error("Failed to save permissions");
    } finally {
      saving = false;
    }
  }

  $effect(() => {
    if (selectedRoleId) void loadRolePermissions(selectedRoleId);
  });

  onMount(() => {
    void loadRoles();
    void loadEntities(entitiesPage);
  });
</script>

<div class="flex flex-col gap-6">
  <div class="flex flex-wrap items-end justify-between gap-4">
    <div>
      <h1 class="text-2xl font-bold tracking-tight">Permissions</h1>
      <p class="mt-1 text-sm text-base-content/60">
        Manage role-based access control
      </p>
    </div>
    <Button
      onclick={savePermissions}
      disabled={saving || !selectedRole || roleLoading}
    >
      {saving ? "Saving..." : "Save Changes"}
    </Button>
  </div>

  <div class="flex flex-col gap-4">
    <div class="flex items-center gap-3">
      <span class="text-sm font-medium">Role:</span>
      <Select.Root
        type="single"
        value={selectedRoleId}
        onValueChange={(value) => (selectedRoleId = value ?? "")}
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
      {#if roleLoading}
        <Spinner class="size-4" />
      {/if}
    </div>

    <div class="overflow-hidden rounded-box border border-base-300 bg-base-100">
      {#if loading && !entities.length}
        <div class="flex items-center justify-center py-12">
          <Spinner class="size-8" />
        </div>
      {:else if entities.length}
        <div class="overflow-x-auto">
          <table class="table table-zebra">
            <thead>
              <tr>
                <th>Entity</th>
                <th>Module</th>
                {#each permissionColumns as [, label] (label)}
                  <th class="text-center">{label}</th>
                {/each}
              </tr>
            </thead>
            <tbody>
              {#each entities as entity (entity.name)}
                <tr>
                  <td>
                    <div class="font-medium">{entity.label}</div>
                    <div class="font-mono text-xs text-base-content/60">
                      {entity.name}
                    </div>
                  </td>
                  <td class="capitalize">{entity.module}</td>
                  {#each permissionColumns as [key] (`${entity.name}-${key}`)}
                    <td class="text-center">
                      <Checkbox
                        checked={Boolean(rolePermissions[entity.name]?.[key])}
                        disabled={roleLoading || saving}
                        onCheckedChange={(value) =>
                          togglePermission(entity.name, key, value === true)}
                      />
                    </td>
                  {/each}
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
        <Pagination
          page={entitiesPage}
          pageSize={entitiesPageSize}
          total={entitiesTotal}
          {loading}
          pageSizeOptions={[10, 25, 50, 100]}
          onchange={setEntitiesPage}
          onpagesizechange={(size) => {
            entitiesPageSize = size;
            setEntitiesPage(1);
          }}
        />
      {:else}
        <Empty.Root class="py-16">
          <Empty.Media variant="icon">
            <ShieldIcon />
          </Empty.Media>
          <Empty.Header>
            <Empty.Title>No entities defined</Empty.Title>
            <Empty.Description>
              Permissions will appear here once entities are registered.
            </Empty.Description>
          </Empty.Header>
        </Empty.Root>
      {/if}
    </div>
  </div>
</div>
