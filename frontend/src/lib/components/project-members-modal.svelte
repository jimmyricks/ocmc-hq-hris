<script lang="ts">
  import * as Dialog from "$lib/components/ui/dialog/index.js";
  import * as Field from "$lib/components/ui/field/index.js";
  import * as Select from "$lib/components/ui/select/index.js";
  import { Button } from "$lib/components/ui/button/index.js";
  import { Input } from "$lib/components/ui/input/index.js";
  import { Avatar, AvatarFallback } from "$lib/components/ui/avatar/index.js";
  import { Separator } from "$lib/components/ui/separator/index.js";
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
    onChanged?: (members: ProjectMember[]) => void;
  }

  let { open = $bindable(false), project = null, onChanged }: Props = $props();

  let projectId = $derived(project?.id ?? "");
  let members = $state<ProjectMember[]>([]);
  let candidates = $state<User[]>([]);
  let loading = $state(false);
  let loadingCandidates = $state(false);
  let candidateError = $state("");
  let selectedUserId = $state("");
  let selectedRole = $state("member");
  let searchQuery = $state("");
  let adding = $state(false);
  let lastLoadedProjectId = "";

  $effect(() => {
    const id = projectId;
    if (!open) {
      lastLoadedProjectId = "";
      return;
    }
    if (!id || lastLoadedProjectId === id) return;
    lastLoadedProjectId = id;
    candidateError = "";
    candidates = [];
    members = [];
    void loadProjectData(id);
  });

  async function loadProjectData(id: string) {
    loading = true;
    loadingCandidates = true;
    try {
      const [projectMembers, projectCandidates] = await Promise.all([
        taskApi.getProjectMembers(id),
        taskApi.getProjectMemberCandidates(id),
      ]);
      members = projectMembers;
      candidates = projectCandidates;
      candidateError = "";
    } catch (err: any) {
      candidateError = err.message || "Failed to load project users";
      toast.error(candidateError);
    } finally {
      loading = false;
      loadingCandidates = false;
    }
  }

  async function loadMembers(id: string): Promise<ProjectMember[]> {
    members = await taskApi.getProjectMembers(id);
    return members;
  }

  let directoryUsers = $derived(candidates);

  function memberUser(member: ProjectMember): User | undefined {
    return directoryUsers.find((u) => u.id === member.user_id);
  }

  function workspaceLabel(user: User | undefined): string {
    return (
      user?.memberships
        ?.map((membership) => membership.workspace_name)
        .join(", ") ?? ""
    );
  }

  function workspaceRoleLabel(user: User | undefined): string {
    if (!user?.memberships?.length) return user ? "Company-wide user" : "";
    return user.memberships
      .map(
        (membership) =>
          `${membership.workspace_name} (${membership.membership_role})`,
      )
      .join(", ");
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
    directoryUsers.filter(
      (user) =>
        user.is_active &&
        !members.some(
          (member) => member.user_id === user.id && member.is_active !== false,
        ),
    ),
  );
  let filteredUsers = $derived.by(() => {
    const query = searchQuery.trim().toLowerCase();
    if (!query) return availableUsers;
    return availableUsers.filter((user) =>
      [user.full_name, user.email, workspaceLabel(user)].some((value) =>
        value?.toLowerCase().includes(query),
      ),
    );
  });
  let selectedUser = $derived(
    directoryUsers.find((user) => user.id === selectedUserId),
  );
  let selectedUserLabel = $derived(
    selectedUser
      ? `${selectedUser.full_name}${workspaceRoleLabel(selectedUser) ? ` — ${workspaceRoleLabel(selectedUser)}` : ""}`
      : "",
  );

  async function handleAdd() {
    if (!selectedUserId || !projectId) return;
    adding = true;
    try {
      await taskApi.addProjectMember(projectId, selectedUserId, selectedRole);
      selectedUserId = "";
      selectedRole = "member";
      searchQuery = "";
      const updatedMembers = await loadMembers(projectId);
      onChanged?.(updatedMembers);
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
      const updatedMembers = await loadMembers(projectId);
      onChanged?.(updatedMembers);
      toast.success("Member removed");
    } catch (err: any) {
      toast.error(err.message || "Failed to remove member");
    }
  }
</script>

<Dialog.Root bind:open>
  <Dialog.Content class="flex h-[80vh] max-w-lg flex-col">
    <Dialog.Header>
      <Dialog.Title>Project Members</Dialog.Title>
      <Dialog.Description>
        {project?.name ?? ""} — members can work on tasks and managers can review
        submissions.
      </Dialog.Description>
    </Dialog.Header>

    <div class="min-h-0 flex-1 space-y-4 overflow-y-auto py-2">
      <!-- Add member -->
      <div class="space-y-2">
        <Field.Field class="gap-1">
          <Field.Label for="member-search">Find user</Field.Label>
          <Input
            id="member-search"
            bind:value={searchQuery}
            placeholder="Search by name, email, or workspace..."
            disabled={loadingCandidates}
          />
        </Field.Field>
        <div class="flex items-end gap-2">
          <Field.Field class="flex-1 gap-1">
            <Field.Label for="member-select">Add member</Field.Label>
            <Select.Root
              type="single"
              value={selectedUserId}
              onValueChange={(v) => (selectedUserId = v)}
            >
              <Select.Trigger id="member-select" class="w-full">
                <span class="truncate">
                  {selectedUser
                    ? selectedUserLabel
                    : loadingCandidates
                      ? "Loading users..."
                      : "Select user..."}
                </span>
              </Select.Trigger>
              <Select.Content>
                {#each filteredUsers as user (user.id)}
                  <Select.Item
                    value={user.id}
                    label={`${user.full_name} — ${workspaceRoleLabel(user)}`}
                  >
                    <div class="flex flex-col">
                      <span>{user.full_name}</span>
                      <span class="text-xs text-base-content/60">
                        {workspaceRoleLabel(user) || user.email}
                      </span>
                    </div>
                  </Select.Item>
                {:else}
                  <div class="px-2 py-1.5 text-xs text-base-content/60">
                    {candidateError
                      ? "Could not load users"
                      : loadingCandidates
                        ? "Loading users..."
                        : "No eligible users found"}
                  </div>
                {/each}
              </Select.Content>
            </Select.Root>
          </Field.Field>
          <Field.Field class="w-36 gap-1">
            <Field.Label for="member-role">Project role</Field.Label>
            <Select.Root
              type="single"
              value={selectedRole}
              onValueChange={(v) => (selectedRole = v)}
            >
              <Select.Trigger id="member-role" class="w-full">
                {selectedRole === "manager" ? "Manager" : "Member"}
              </Select.Trigger>
              <Select.Content>
                <Select.Item value="member" label="Member">Member</Select.Item>
                <Select.Item value="manager" label="Manager">
                  Manager
                </Select.Item>
              </Select.Content>
            </Select.Root>
          </Field.Field>
          <Button disabled={!selectedUserId || adding} onclick={handleAdd}>
            {adding ? "Adding..." : "Add"}
          </Button>
        </div>
      </div>

      <Separator />

      <!-- Current members -->
      <div class="space-y-2">
        <p class="text-sm font-medium">Current Members</p>
        {#if loading}
          <p class="text-sm text-base-content/60">Loading...</p>
        {:else if members.length === 0}
          <p class="text-sm text-base-content/60">No members yet.</p>
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
                  <p class="text-xs text-base-content/60 truncate">
                    {user?.email ?? ""}
                  </p>
                  <p class="text-xs text-base-content/60 truncate">
                    {workspaceRoleLabel(user)}
                    {member.role === "manager" ? " · Project manager" : ""}
                  </p>
                </div>
                <Button
                  size="sm"
                  variant="ghost"
                  class="text-error hover:text-error"
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
