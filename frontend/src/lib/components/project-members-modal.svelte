<script lang="ts">
  import * as Dialog from "$lib/components/native/dialog/index.js";
  import * as Field from "$lib/components/native/field/index.js";
  import * as Select from "$lib/components/native/select/index.js";
  import { Button } from "$lib/components/native/button/index.js";
  import {
    Avatar,
    AvatarFallback,
  } from "$lib/components/native/avatar/index.js";
  import { Separator } from "$lib/components/native/separator/index.js";
  import { toast } from "$lib/notifications";
  import { taskApi } from "$lib/task-manager/api.js";
  import type {
    Project,
    ProjectMember,
    User,
  } from "$lib/task-manager/types.js";

  interface Props {
    open?: boolean;
    project?: Project | null;
    users?: User[];
    onChanged?: () => void;
  }

  let {
    open = $bindable(false),
    project = null,
    users = [],
    onChanged,
  }: Props = $props();

  let members = $state<ProjectMember[]>([]);
  let loading = $state(false);
  let selectedUserId = $state("");
  let adding = $state(false);

  $effect(() => {
    if (open && project?.id) {
      loadMembers();
    }
  });

  async function loadMembers() {
    if (!project?.id) return;
    loading = true;
    try {
      members = await taskApi.getProjectMembers(project.id);
    } catch (err: any) {
      toast.error(err.message || "Failed to load members");
    } finally {
      loading = false;
    }
  }

  function memberUser(member: ProjectMember): User | undefined {
    return users.find((u) => u.id === member.user_id);
  }

  function initials(name: string): string {
    return name
      .split(" ")
      .map((p) => p[0])
      .filter(Boolean)
      .slice(0, 2)
      .join("")
      .toUpperCase();
  }

  // Users not already members
  let availableUsers = $derived(
    users.filter((u) => !members.some((m) => m.user_id === u.id)),
  );

  async function handleAdd() {
    if (!selectedUserId || !project?.id) return;
    adding = true;
    try {
      await taskApi.addProjectMember(project.id, selectedUserId);
      selectedUserId = "";
      await loadMembers();
      onChanged?.();
      toast.success("Member added");
    } catch (err: any) {
      toast.error(err.message || "Failed to add member");
    } finally {
      adding = false;
    }
  }

  async function handleRemove(member: ProjectMember) {
    try {
      await taskApi.removeProjectMember(member.id);
      await loadMembers();
      onChanged?.();
      toast.success("Member removed");
    } catch (err: any) {
      toast.error(err.message || "Failed to remove member");
    }
  }
</script>

<Dialog.Root bind:open>
  <Dialog.Content class="max-w-lg">
    <Dialog.Header>
      <Dialog.Title>Project Members</Dialog.Title>
      <Dialog.Description>
        {project?.name ?? ""} — only members can be assigned tasks.
      </Dialog.Description>
    </Dialog.Header>

    <div class="space-y-4 py-2">
      <!-- Add member -->
      <div class="flex items-end gap-2">
        <Field.Field class="flex-1 gap-1">
          <Field.Label for="member-select">Add member</Field.Label>
          <Select.Root
            type="single"
            value={selectedUserId}
            onValueChange={(v) => (selectedUserId = v)}
          >
            <Select.Trigger id="member-select" class="w-full">
              <span class="truncate"
                >{selectedUserId
                  ? (users.find((u) => u.id === selectedUserId)?.full_name ??
                    "Select user...")
                  : "Select user..."}</span
              >
            </Select.Trigger>
            <Select.Content>
              {#each availableUsers as user (user.id)}
                <Select.Item value={user.id} label={user.full_name}>
                  {user.full_name}
                </Select.Item>
              {:else}
                <div class="px-2 py-1.5 text-xs text-muted-foreground">
                  All users are already members
                </div>
              {/each}
            </Select.Content>
          </Select.Root>
        </Field.Field>
        <Button disabled={!selectedUserId || adding} onclick={handleAdd}>
          {adding ? "Adding..." : "Add"}
        </Button>
      </div>

      <Separator />

      <!-- Current members -->
      <div class="space-y-2">
        <p class="text-sm font-medium">Current Members</p>
        {#if loading}
          <p class="text-sm text-muted-foreground">Loading...</p>
        {:else if members.length === 0}
          <p class="text-sm text-muted-foreground">No members yet.</p>
        {:else}
          <div class="space-y-1">
            {#each members as member (member.id)}
              {@const user = memberUser(member)}
              <div class="flex items-center gap-3 rounded-lg border p-2">
                <Avatar class="size-8">
                  <AvatarFallback class="text-xs">
                    {initials(user?.full_name ?? member.user_id)}
                  </AvatarFallback>
                </Avatar>
                <div class="flex-1 min-w-0">
                  <p class="text-sm font-medium truncate">
                    {user?.full_name ?? member.user_id}
                  </p>
                  <p class="text-xs text-muted-foreground truncate">
                    {user?.email ?? ""}
                  </p>
                </div>
                <Button
                  size="sm"
                  variant="ghost"
                  class="text-destructive hover:text-destructive"
                  onclick={() => handleRemove(member)}
                >
                  Remove
                </Button>
              </div>
            {/each}
          </div>
        {/if}
      </div>
    </div>

    <Dialog.Footer>
      <Button variant="outline" onclick={() => (open = false)}>Done</Button>
    </Dialog.Footer>
  </Dialog.Content>
</Dialog.Root>
