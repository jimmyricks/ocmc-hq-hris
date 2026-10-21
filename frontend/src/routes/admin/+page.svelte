<script lang="ts">
  import { onMount } from "svelte";
  import * as Table from "$lib/components/ui/table/index.js";
  import * as Dialog from "$lib/components/ui/dialog/index.js";
  import { Button } from "$lib/components/ui/button/index.js";
  import { Badge } from "$lib/components/ui/badge/index.js";
  import { Spinner } from "$lib/components/ui/spinner/index.js";
  import * as Empty from "$lib/components/ui/empty/index.js";
  import { apiJSON } from "$lib/api/index.js";
  import { toast } from "$lib/notifications";
  import UsersIcon from "@lucide/svelte/icons/users";

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

  let users = $state<User[]>([]);
  let roles = $state<Role[]>([]);
  let loading = $state(true);
  let deleteDialogOpen = $state(false);
  let userToDelete = $state<string | null>(null);

  async function loadUsers() {
    loading = true;
    try {
      const [usersData, rolesData] = await Promise.all([
        apiJSON("/api/admin/users"),
        apiJSON("/api/admin/roles"),
      ]);
      users = usersData.data?.users || usersData.data || [];
      roles = rolesData.data || [];
    } catch (error) {
      console.error("Failed to load data:", error);
    } finally {
      loading = false;
    }
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
      await loadUsers();
    } catch (error) {
      console.error("Failed to delete user:", error);
      toast.error("Failed to delete user");
    } finally {
      deleteDialogOpen = false;
      userToDelete = null;
    }
  }

  onMount(() => {
    loadUsers();
  });
</script>

<div class="flex flex-col gap-6">
  <div class="flex items-center justify-between">
    <h1 class="text-2xl font-bold tracking-tight">Users</h1>
    <Button>Add User</Button>
  </div>

  <div class="border rounded-xl">
    {#if loading}
      <div class="flex items-center justify-center py-12">
        <Spinner class="size-8" />
      </div>
    {:else if users.length > 0}
      <div class="overflow-x-auto">
        <Table.Root>
          <Table.Header>
            <Table.Row>
              <Table.Head>User</Table.Head>
              <Table.Head>Email</Table.Head>
              <Table.Head>Roles</Table.Head>
              <Table.Head>Status</Table.Head>
              <Table.Head class="text-right">Actions</Table.Head>
            </Table.Row>
          </Table.Header>
          <Table.Body>
            {#each users as user (user.id)}
              <Table.Row>
                <Table.Cell>
                  <div class="font-medium">{user.full_name}</div>
                  <div class="text-sm text-base-content/60">
                    {user.username}
                  </div>
                </Table.Cell>
                <Table.Cell>{user.email}</Table.Cell>
                <Table.Cell>
                  <div class="flex flex-wrap gap-1">
                    {#each user.roles as role (role.name)}
                      <Badge variant="secondary">{role.name}</Badge>
                    {/each}
                  </div>
                </Table.Cell>
                <Table.Cell>
                  <Badge variant={user.is_active ? "default" : "secondary"}>
                    {user.is_active ? "Active" : "Inactive"}
                  </Badge>
                </Table.Cell>
                <Table.Cell class="text-right">
                  <Button variant="ghost" size="sm">Edit</Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onclick={() => openDeleteDialog(user.id)}>Delete</Button
                  >
                </Table.Cell>
              </Table.Row>
            {/each}
          </Table.Body>
        </Table.Root>
      </div>
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
