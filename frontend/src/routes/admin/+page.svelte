<script lang="ts">
  import { onMount } from "svelte";
  import * as Dialog from "$lib/components/ui/dialog/index.js";
  import { Button } from "$lib/components/ui/button/index.js";
  import { Badge } from "$lib/components/ui/badge/index.js";
  import { Spinner } from "$lib/components/ui/spinner/index.js";
  import * as Empty from "$lib/components/ui/empty/index.js";
  import { apiJSON, toPaginatedResult } from "$lib/api/index.js";
  import { toast } from "$lib/notifications";
  import { useAppState } from "$lib/app-state.svelte.js";
  import Pagination from "$lib/components/pagination.svelte";
  import UsersIcon from "@lucide/svelte/icons/users";
  import PencilIcon from "@lucide/svelte/icons/pencil";
  import Trash2Icon from "@lucide/svelte/icons/trash-2";

  interface User {
    id: string;
    full_name: string;
    username: string;
    email: string;
    roles: Array<{ name: string }>;
    is_active: boolean;
  }

  interface Role {
    id: string;
    name: string;
  }

  const appState = useAppState();
  let users = $state<User[]>([]);
  let roles = $state<Role[]>([]);
  let loading = $state(true);
  let usersPage = $state(appState.tablePage("admin-users"));
  let usersPageSize = $state(25);
  let usersTotal = $state(0);
  let deleteDialogOpen = $state(false);
  let userToDelete = $state<string | null>(null);

  async function loadUsers(page = usersPage) {
    loading = true;
    try {
      const usersData = await apiJSON(
        `/api/admin/users?page=${page}&page_size=${usersPageSize}`,
      );
      const result = toPaginatedResult<User>(usersData, page, usersPageSize, [
        "users",
      ]);
      if (!result.items.length && result.total > 0 && page > 1) {
        const lastPage = Math.ceil(result.total / usersPageSize);
        return loadUsers(lastPage);
      }
      users = result.items;
      usersTotal = result.total;
      usersPage = result.page;
      appState.rememberTablePage("admin-users", usersPage);
    } catch (error) {
      console.error("Failed to load data:", error);
    } finally {
      loading = false;
    }
  }

  async function loadRoles() {
    try {
      const rolesData = await apiJSON("/api/admin/roles");
      roles = rolesData.data || [];
    } catch (error) {
      console.error("Failed to load roles:", error);
    }
  }

  function setUsersPage(page: number) {
    usersPage = page;
    appState.rememberTablePage("admin-users", page);
    void loadUsers(page);
  }

  function openDeleteDialog(userId: string) {
    userToDelete = userId;
    deleteDialogOpen = true;
  }

  async function confirmDelete() {
    if (!userToDelete) return;
    try {
      await apiJSON(`/api/admin/users/${userToDelete}`, { method: "DELETE" });
      toast.success("User deleted successfully");
      await loadUsers(usersPage);
    } catch (error) {
      console.error("Failed to delete user:", error);
      toast.error("Failed to delete user");
    } finally {
      deleteDialogOpen = false;
      userToDelete = null;
    }
  }

  onMount(() => {
    void loadRoles();
    void loadUsers(usersPage);
  });
</script>

<div class="flex flex-col gap-6">
  <div class="flex flex-wrap items-end justify-between gap-4">
    <h1 class="text-2xl font-bold tracking-tight">Users</h1>
    <Button>Add User</Button>
  </div>

  <div class="overflow-hidden rounded-box border border-base-300 bg-base-100">
    {#if loading}
      <div class="flex items-center justify-center py-12">
        <Spinner class="size-8" />
      </div>
    {:else if users.length > 0}
      <div class="overflow-x-auto">
        <table class="table table-zebra">
          <thead>
            <tr>
              <th>User</th>
              <th>Email</th>
              <th>Roles</th>
              <th>Status</th>
              <th class="text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {#each users as user (user.id)}
              <tr>
                <td>
                  <div class="font-medium">{user.full_name}</div>
                  <div class="text-sm text-base-content/60">
                    {user.username}
                  </div>
                </td>
                <td>{user.email}</td>
                <td>
                  <div class="flex flex-wrap gap-1">
                    {#each user.roles as role (role.name)}
                      <Badge variant="secondary">{role.name}</Badge>
                    {/each}
                  </div>
                </td>
                <td>
                  <Badge variant={user.is_active ? "default" : "secondary"}>
                    {user.is_active ? "Active" : "Inactive"}
                  </Badge>
                </td>
                <td class="text-right">
                  <button
                    class="btn btn-ghost btn-sm btn-square"
                    type="button"
                    aria-label="Edit user"
                  >
                    <PencilIcon size={15} />
                  </button>
                  <button
                    class="btn btn-ghost btn-sm btn-square text-error"
                    type="button"
                    aria-label="Delete user"
                    onclick={() => openDeleteDialog(user.id)}
                  >
                    <Trash2Icon size={15} />
                  </button>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
      <Pagination
        page={usersPage}
        pageSize={usersPageSize}
        total={usersTotal}
        {loading}
        pageSizeOptions={[10, 25, 50, 100]}
        onchange={setUsersPage}
        onpagesizechange={(size) => {
          usersPageSize = size;
          setUsersPage(1);
        }}
      />
    {:else}
      <Empty.Root class="py-16">
        <Empty.Media variant="icon">
          <UsersIcon />
        </Empty.Media>
        <Empty.Header>
          <Empty.Title>No users found</Empty.Title>
          <Empty.Description
            >Users will appear here once added.</Empty.Description
          >
        </Empty.Header>
      </Empty.Root>
    {/if}
  </div>

  <Dialog.Root bind:open={deleteDialogOpen}>
    <Dialog.Content>
      <Dialog.Header>
        <Dialog.Title>Delete User</Dialog.Title>
        <Dialog.Description>
          Are you sure you want to delete this user? This action cannot be
          undone.
        </Dialog.Description>
      </Dialog.Header>
      <Dialog.Footer>
        <Button variant="outline" onclick={() => (deleteDialogOpen = false)}>
          Cancel
        </Button>
        <Button variant="destructive" onclick={confirmDelete}>Delete</Button>
      </Dialog.Footer>
    </Dialog.Content>
  </Dialog.Root>
</div>
