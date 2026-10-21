<script lang="ts">
  import { onMount } from "svelte";
  import * as Card from "$lib/components/ui/card/index.js";
  import * as Field from "$lib/components/ui/field/index.js";
  import * as Select from "$lib/components/ui/select/index.js";
  import { Button } from "$lib/components/ui/button/index.js";
  import { Input } from "$lib/components/ui/input/index.js";
  import { Badge } from "$lib/components/ui/badge/index.js";
  import { toast } from "$lib/notifications";
  import { taskApi } from "$lib/task-manager/api.js";
  import { workspaceApi } from "$lib/workspaces/api.js";
  import type { WorkspaceContext } from "$lib/workspaces/types.js";

  type MembershipRole = "member" | "supervisor";
  type MappingEntity = "project" | "task_type";
  type AdminUser = {
    id: string;
    full_name: string;
    username?: string;
    email: string;
  };
  type Membership = {
    id: string;
    user_id: string;
    membership_role: MembershipRole;
    is_home: boolean;
  };
  type AdminResource = {
    id: string;
    workspace_id: string;
    name: string;
    resource_type: string;
  };
  type UnmappedRecord = {
    id: string;
    name: string;
    unit_rate?: number;
    unit?: string;
  };
  type UnmappedRecords = {
    projects: UnmappedRecord[];
    task_types: UnmappedRecord[];
  };

  let context = $state<WorkspaceContext | null>(null);
  let users = $state<AdminUser[]>([]);
  let members = $state<Membership[]>([]);
  let resources = $state<AdminResource[]>([]);
  let unmapped = $state<UnmappedRecords>({
    projects: [],
    task_types: [],
  });
  let workspaceId = $state("");
  let workspaceColor = $state("#45aeee");
  let userId = $state("");
  let membershipRole = $state<MembershipRole>("member");
  let isHome = $state(true);
  let mappingEntity = $state<MappingEntity>("project");
  let mappingRecordId = $state("");
  let loading = $state(true);
  let savingMembership = $state(false);
  let savingMapping = $state(false);
  let resourceName = $state("");
  let resourceType = $state<"room" | "equipment" | "instructor" | "other">(
    "room",
  );
  let savingResource = $state(false);

  const selectedWorkspace = $derived(
    context?.workspaces.find((workspace) => workspace.id === workspaceId),
  );
  const mappingRecords = $derived(
    mappingEntity === "project"
      ? unmapped.projects
      : mappingEntity === "task_type"
        ? unmapped.task_types
        : [],
  );

  onMount(load);

  async function load() {
    loading = true;
    try {
      const [workspaceData, userData, unmappedData] = await Promise.all([
        workspaceApi.getContext(),
        taskApi.getUsers(),
        workspaceApi.getUnmapped(),
      ]);
      context = workspaceData;
      users = userData as AdminUser[];
      unmapped = unmappedData;
      workspaceId =
        workspaceData.active_workspace_id ??
        workspaceData.workspaces[0]?.id ??
        "";
      workspaceColor =
        workspaceData.workspaces.find(
          (workspace) => workspace.id === workspaceId,
        )?.color ?? "#45aeee";
      if (workspaceId) await Promise.all([loadMembers(), loadResources()]);
    } catch (error) {
      console.error("Failed to load workspace administration:", error);
      toast.error("Could not load workspace administration");
    } finally {
      loading = false;
    }
  }

  async function loadMembers() {
    if (!workspaceId) return;
    members = await workspaceApi.getMembers(workspaceId);
  }

  async function loadResources() {
    if (!workspaceId) return;
    resources = await workspaceApi.getResources(workspaceId);
  }

  function selectWorkspace(value: string | undefined) {
    if (!value) return;
    workspaceId = value;
    workspaceColor =
      context?.workspaces.find((workspace) => workspace.id === value)?.color ??
      "#45aeee";
    Promise.all([loadMembers(), loadResources()]).catch((error) => {
      console.error("Failed to load workspace members:", error);
    });
  }

  function userName(id: string) {
    const user = users.find((item) => item.id === id);
    return user?.full_name || user?.username || id;
  }

  async function saveColor() {
    if (!workspaceId) return;
    try {
      await workspaceApi.updateWorkspace(workspaceId, {
        color: workspaceColor,
      });
      if (context) {
        context = {
          ...context,
          workspaces: context.workspaces.map((workspace) =>
            workspace.id === workspaceId
              ? { ...workspace, color: workspaceColor }
              : workspace,
          ),
        };
      }
      toast.success("Workspace color saved");
    } catch (error: any) {
      toast.error(error.message || "Could not save workspace color");
    }
  }

  async function addMembership() {
    if (!workspaceId || !userId) return;
    savingMembership = true;
    try {
      await workspaceApi.assignMember(
        workspaceId,
        userId,
        membershipRole,
        isHome,
      );
      userId = "";
      await loadMembers();
      toast.success("Workspace access assigned");
    } catch (error: any) {
      toast.error(error.message || "Could not assign workspace access");
    } finally {
      savingMembership = false;
    }
  }

  async function removeMembership(member: Membership) {
    try {
      await workspaceApi.removeMember(workspaceId, member.id);
      await loadMembers();
      toast.success("Workspace access removed");
    } catch (error: any) {
      toast.error(error.message || "Could not remove workspace access");
    }
  }

  async function mapRecord() {
    if (!workspaceId || !mappingRecordId) return;
    savingMapping = true;
    try {
      await workspaceApi.mapLegacy(mappingEntity, mappingRecordId, workspaceId);
      mappingRecordId = "";
      unmapped = await workspaceApi.getUnmapped();
      toast.success("Legacy record mapped");
    } catch (error: any) {
      toast.error(error.message || "Could not map legacy record");
    } finally {
      savingMapping = false;
    }
  }

  async function addResource() {
    if (!workspaceId || !resourceName.trim()) return;
    savingResource = true;
    try {
      await workspaceApi.createResource({
        workspace_id: workspaceId,
        name: resourceName.trim(),
        resource_type: resourceType,
      });
      resourceName = "";
      await loadResources();
      toast.success("Workspace resource added");
    } catch (error: any) {
      toast.error(error.message || "Could not add resource");
    } finally {
      savingResource = false;
    }
  }

  async function deactivateResource(resource: AdminResource) {
    try {
      await workspaceApi.updateResource(resource.id, { is_active: false });
      await loadResources();
      toast.success("Resource deactivated");
    } catch (error: any) {
      toast.error(error.message || "Could not deactivate resource");
    }
  }
</script>

<svelte:head>
  <title>Workspaces · OCMC HQ</title>
</svelte:head>

<div class="flex flex-col gap-6">
  <header>
    <p
      class="text-xs font-semibold uppercase tracking-[0.14em] text-base-content/60"
    >
      HQ administration
    </p>
    <h1 class="mt-2 text-3xl font-semibold tracking-tight">Workspaces</h1>
    <p class="mt-2 text-sm text-base-content/60">
      Configure company access, calendar colors, and legacy project/rate
      ownership.
    </p>
  </header>

  {#if loading}
    <p class="text-sm text-base-content/60">
      Loading workspace administration…
    </p>
  {:else}
    <Card.Root>
      <Card.Header>
        <Card.Title>Company workspaces</Card.Title>
        <Card.Description>
          Company color is inherited by every activity in its calendar.
        </Card.Description>
      </Card.Header>
      <Card.Content class="flex flex-col gap-5">
        <Field.Field>
          <Field.Label for="workspace-select">Selected company</Field.Label>
          <Select.Root
            type="single"
            value={workspaceId}
            onValueChange={selectWorkspace}
          >
            <Select.Trigger id="workspace-select" class="w-full sm:max-w-md">
              <span class="truncate"
                >{selectedWorkspace?.name ?? "Select workspace"}</span
              >
            </Select.Trigger>
            <Select.Content>
              <Select.Group>
                {#each context?.workspaces ?? [] as workspace (workspace.id)}
                  <Select.Item value={workspace.id} label={workspace.name}>
                    {workspace.name}
                  </Select.Item>
                {/each}
              </Select.Group>
            </Select.Content>
          </Select.Root>
        </Field.Field>

        {#if selectedWorkspace}
          <div class="flex flex-wrap items-end gap-3">
            <Field.Field class="w-40">
              <Field.Label for="workspace-color">Calendar color</Field.Label>
              <Input
                id="workspace-color"
                type="color"
                bind:value={workspaceColor}
                class="p-1"
              />
            </Field.Field>
            <Button onclick={saveColor}>Save color</Button>
          </div>
        {/if}

        <section class="flex flex-col gap-4 rounded-xl border p-4">
          <div>
            <h2 class="font-semibold">Rooms and schedulable resources</h2>
            <p class="mt-1 text-xs text-base-content/60">
              These resources can be reserved by calendar events and recurring
              sessions.
            </p>
          </div>
          <div
            class="grid gap-3 sm:grid-cols-[minmax(0,1fr)_180px_auto] sm:items-end"
          >
            <Field.Field>
              <Field.Label for="resource-name">Resource name</Field.Label>
              <Input id="resource-name" bind:value={resourceName} />
            </Field.Field>
            <Field.Field>
              <Field.Label for="resource-type">Resource type</Field.Label>
              <Select.Root
                type="single"
                value={resourceType}
                onValueChange={(value) =>
                  (resourceType = (value as typeof resourceType) ?? "room")}
              >
                <Select.Trigger id="resource-type" class="w-full">
                  <span class="capitalize">{resourceType}</span>
                </Select.Trigger>
                <Select.Content>
                  <Select.Group>
                    <Select.Item value="room" label="Room">Room</Select.Item>
                    <Select.Item value="equipment" label="Equipment">
                      Equipment
                    </Select.Item>
                    <Select.Item value="instructor" label="Instructor">
                      Instructor
                    </Select.Item>
                    <Select.Item value="other" label="Other">Other</Select.Item>
                  </Select.Group>
                </Select.Content>
              </Select.Root>
            </Field.Field>
            <Button
              disabled={!workspaceId || !resourceName.trim() || savingResource}
              onclick={addResource}
            >
              {savingResource ? "Saving…" : "Add resource"}
            </Button>
          </div>
          <div class="flex flex-wrap gap-2">
            {#each resources as resource (resource.id)}
              <div
                class="flex items-center gap-2 rounded-lg bg-base-200/50 px-3 py-2"
              >
                <span class="text-sm font-medium">{resource.name}</span>
                <Badge variant="secondary">{resource.resource_type}</Badge>
                <Button
                  variant="ghost"
                  size="sm"
                  onclick={() => deactivateResource(resource)}
                >
                  Deactivate
                </Button>
              </div>
            {:else}
              <p class="text-xs text-base-content/60">
                No resources configured for this workspace.
              </p>
            {/each}
          </div>
        </section>

        <div class="grid gap-6 xl:grid-cols-2">
          <section class="flex flex-col gap-4 rounded-xl border p-4">
            <div>
              <h2 class="font-semibold">Assign company access</h2>
              <p class="mt-1 text-xs text-base-content/60">
                Members have one home company. Supervisors can have several
                assigned companies.
              </p>
            </div>
            <Field.Field>
              <Field.Label for="workspace-user">User</Field.Label>
              <Select.Root
                type="single"
                value={userId}
                onValueChange={(value) => (userId = value ?? "")}
              >
                <Select.Trigger id="workspace-user" class="w-full">
                  <span class="truncate">
                    {userId ? userName(userId) : "Select user"}
                  </span>
                </Select.Trigger>
                <Select.Content>
                  <Select.Group>
                    {#each users as user (user.id)}
                      <Select.Item
                        value={user.id}
                        label={user.full_name || user.username || user.email}
                      >
                        {user.full_name || user.username || user.email}
                      </Select.Item>
                    {/each}
                  </Select.Group>
                </Select.Content>
              </Select.Root>
            </Field.Field>
            <div class="grid gap-3 sm:grid-cols-2">
              <Field.Field>
                <Field.Label for="membership-role">Workspace role</Field.Label>
                <Select.Root
                  type="single"
                  value={membershipRole}
                  onValueChange={(value) => {
                    membershipRole = (value as MembershipRole) ?? "member";
                    if (membershipRole === "member") isHome = true;
                  }}
                >
                  <Select.Trigger id="membership-role" class="w-full">
                    <span class="capitalize">{membershipRole}</span>
                  </Select.Trigger>
                  <Select.Content>
                    <Select.Group>
                      <Select.Item value="member" label="Member"
                        >Member</Select.Item
                      >
                      <Select.Item value="supervisor" label="Supervisor">
                        Supervisor
                      </Select.Item>
                    </Select.Group>
                  </Select.Content>
                </Select.Root>
              </Field.Field>
              <Field.Field>
                <Field.Label for="home-workspace"
                  >Workspace assignment</Field.Label
                >
                <Select.Root
                  type="single"
                  value={isHome || membershipRole === "member" ? "yes" : "no"}
                  onValueChange={(value) => {
                    isHome = value === "yes";
                    if (membershipRole === "member") isHome = true;
                  }}
                >
                  <Select.Trigger id="home-workspace" class="w-full">
                    <span>
                      {isHome || membershipRole === "member"
                        ? "Home workspace"
                        : "Additional supervisor access"}
                    </span>
                  </Select.Trigger>
                  <Select.Content>
                    <Select.Group>
                      <Select.Item value="yes" label="Home workspace">
                        Home workspace
                      </Select.Item>
                      {#if membershipRole === "supervisor"}
                        <Select.Item
                          value="no"
                          label="Additional supervisor access"
                        >
                          Additional supervisor access
                        </Select.Item>
                      {/if}
                    </Select.Group>
                  </Select.Content>
                </Select.Root>
              </Field.Field>
            </div>
            <Button
              class="self-start"
              disabled={!workspaceId || !userId || savingMembership}
              onclick={addMembership}
            >
              {savingMembership ? "Saving…" : "Assign access"}
            </Button>

            <div class="flex flex-col gap-2 border-t pt-4">
              {#each members as member (member.id)}
                <div
                  class="flex items-center justify-between gap-3 rounded-lg bg-base-200/40 px-3 py-2"
                >
                  <div class="min-w-0">
                    <p class="truncate text-sm font-medium">
                      {userName(member.user_id)}
                    </p>
                    <div class="mt-1 flex gap-2">
                      <Badge variant="secondary">{member.membership_role}</Badge
                      >
                      {#if member.is_home}
                        <Badge>Home</Badge>
                      {/if}
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onclick={() => removeMembership(member)}
                  >
                    Remove
                  </Button>
                </div>
              {:else}
                <p class="text-xs text-base-content/60">
                  No members assigned to this workspace yet.
                </p>
              {/each}
            </div>
          </section>

          <section class="flex flex-col gap-4 rounded-xl border p-4">
            <div>
              <h2 class="font-semibold">Map existing records</h2>
              <p class="mt-1 text-xs text-base-content/60">
                Unmapped legacy records remain hidden from regular workspace
                users until assigned.
              </p>
            </div>
            <Field.Field>
              <Field.Label for="mapping-entity">Record type</Field.Label>
              <Select.Root
                type="single"
                value={mappingEntity}
                onValueChange={(value) => {
                  mappingEntity = (value as MappingEntity) ?? "project";
                  mappingRecordId = "";
                }}
              >
                <Select.Trigger id="mapping-entity" class="w-full">
                  <span class="capitalize"
                    >{mappingEntity.replace("_", " ")}</span
                  >
                </Select.Trigger>
                <Select.Content>
                  <Select.Group>
                    <Select.Item value="project" label="Project"
                      >Project</Select.Item
                    >
                    <Select.Item value="task_type" label="Task type">
                      Task type
                    </Select.Item>
                  </Select.Group>
                </Select.Content>
              </Select.Root>
            </Field.Field>
            <Field.Field>
              <Field.Label for="legacy-record">Unmapped record</Field.Label>
              <Select.Root
                type="single"
                value={mappingRecordId}
                onValueChange={(value) => (mappingRecordId = value ?? "")}
              >
                <Select.Trigger id="legacy-record" class="w-full">
                  <span class="truncate">
                    {mappingRecords.find(
                      (record) => record.id === mappingRecordId,
                    )?.name ??
                      (mappingRecords.length
                        ? "Select record"
                        : "No unmapped records")}
                  </span>
                </Select.Trigger>
                <Select.Content>
                  <Select.Group>
                    {#each mappingRecords as record (record.id)}
                      <Select.Item value={record.id} label={record.name}>
                        {record.name}
                      </Select.Item>
                    {/each}
                  </Select.Group>
                </Select.Content>
              </Select.Root>
            </Field.Field>
            <Button
              class="self-start"
              disabled={!workspaceId || !mappingRecordId || savingMapping}
              onclick={mapRecord}
            >
              {savingMapping ? "Mapping…" : "Map to selected company"}
            </Button>
          </section>
        </div>
      </Card.Content>
    </Card.Root>
  {/if}
</div>
