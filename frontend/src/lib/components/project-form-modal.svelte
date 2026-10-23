<script lang="ts">
  import * as Dialog from "$lib/components/ui/dialog/index.js";
  import * as Field from "$lib/components/ui/field/index.js";
  import * as Select from "$lib/components/ui/select/index.js";
  import { Button } from "$lib/components/ui/button/index.js";
  import { Input } from "$lib/components/ui/input/index.js";
  import { Textarea } from "$lib/components/ui/textarea/index.js";
  import { toast } from "$lib/notifications";
  import { saveEntity } from "$lib/api/index.js";
  import { workspaceApi } from "$lib/workspaces/api.js";
  import { useAppState } from "$lib/app-state.svelte.js";
  import type { Project, User } from "$lib/task-manager/types.js";

  interface Props {
    open?: boolean;
    project?: Project | null;
    users?: User[];
    onSaved?: (project: Project) => void;
  }

  let {
    open = $bindable(false),
    project = null,
    users = [],
    onSaved,
  }: Props = $props();

  const appState = useAppState();
  const workspaceContext = $derived(appState.workspaceContext);
  let isEdit = $derived(!!project?.id);
  let saving = $state(false);
  let name = $state("");
  let color = $state("#45aeee");
  let icon = $state("folder");
  let managerId = $state("");
  let description = $state("");
  let workspaceId = $state("");
  let teamId = $state("");
  let startDate = $state("");
  let endDate = $state("");
  let isContinuous = $state(false);
  let teams = $state<Array<{ id: string; name: string }>>([]);
  let loadingTeams = $state(false);
  const canChooseWorkspace = $derived(
    Boolean(
      workspaceContext?.can_manage && workspaceContext.is_global && !isEdit,
    ),
  );

  const COLORS = [
    "#45aeee",
    "#e8488a",
    "#ee8134",
    "#3db95c",
    "#4ba8c0",
    "#e93f33",
    "#1a1a1a",
    "#54b8f7",
    "#fb5d9b",
    "#eee455",
  ];

  const ICONS = [
    "folder",
    "briefcase",
    "rocket",
    "code",
    "design",
    "marketing",
  ];

  $effect.pre(() => {
    name = project?.name ?? "";
    color = project?.color ?? "#45aeee";
    icon = project?.icon ?? "folder";
    managerId = project?.manager_id ?? "";
    description = project?.description ?? "";
    teamId = project?.team_id ?? "";
    startDate = project?.start_date?.slice(0, 10) ?? "";
    endDate = project?.end_date?.slice(0, 10) ?? "";
    isContinuous = project?.is_continuous ?? false;
    if (project?.workspace_id) workspaceId = project.workspace_id;
  });

  $effect(() => {
    if (!open || workspaceId) return;
    workspaceId =
      project?.workspace_id ?? workspaceContext?.active_workspace_id ?? "";
  });

  $effect(() => {
    if (!open || !workspaceId) {
      teams = [];
      return;
    }
    loadingTeams = true;
    workspaceApi
      .getTeams(workspaceId)
      .then((rows) => (teams = rows))
      .catch(() => (teams = []))
      .finally(() => (loadingTeams = false));
  });

  function userName(id: string) {
    return users.find((u) => u.id === id)?.full_name ?? "Select manager...";
  }

  function updateContinuous(event: Event) {
    isContinuous = (event.currentTarget as HTMLInputElement).checked;
    if (isContinuous) endDate = "";
  }

  async function handleSave() {
    if (!name.trim()) {
      toast.error("Project name is required");
      return;
    }
    if (!workspaceContext?.can_manage) {
      toast.error("Workspace supervisor access is required to manage projects");
      return;
    }
    if (!isEdit && !workspaceId) {
      toast.error("Select a workspace before creating a project");
      return;
    }
    saving = true;
    try {
      const data: Record<string, any> = {
        name: name.trim(),
        color,
        icon,
        manager_id: managerId || undefined,
        description: description.trim() || undefined,
        team_id: teamId || null,
        start_date: startDate || null,
        end_date: isContinuous ? null : endDate || null,
        is_continuous: isContinuous,
      };
      let saved: Project;
      if (isEdit && project?.id) {
        const res = await saveEntity(
          "project",
          { ...project, ...data },
          project.id,
        );
        saved = res.data as Project;
      } else {
        const res = await saveEntity("project", {
          ...data,
          workspace_id: workspaceId,
        });
        saved = res.data as Project;
      }
      toast.success(isEdit ? "Project updated" : "Project created");
      open = false;
      onSaved?.(saved);
    } catch (err: any) {
      toast.error(err.message || "Failed to save project");
    } finally {
      saving = false;
    }
  }
</script>

<Dialog.Root bind:open>
  <Dialog.Content class="max-w-lg">
    <Dialog.Header>
      <Dialog.Title>{isEdit ? "Configure Project" : "New Project"}</Dialog.Title
      >
      <Dialog.Description>
        {isEdit
          ? "Update project details."
          : "Create a new project. It will appear in the sidebar."}
      </Dialog.Description>
    </Dialog.Header>

    <div class="space-y-4 py-2">
      {#if canChooseWorkspace}
        <Field.Field class="gap-1">
          <Field.Label for="project-workspace">Workspace</Field.Label>
          <Select.Root
            type="single"
            value={workspaceId}
            onValueChange={(value) => {
              workspaceId = value ?? "";
              teamId = "";
            }}
          >
            <Select.Trigger id="project-workspace" class="w-full">
              <span class="truncate">
                {workspaceContext?.workspaces.find(
                  (workspace) => workspace.id === workspaceId,
                )?.name ?? "Select workspace..."}
              </span>
            </Select.Trigger>
            <Select.Content>
              <Select.Group>
                {#each workspaceContext?.workspaces ?? [] as workspace (workspace.id)}
                  <Select.Item value={workspace.id} label={workspace.name}>
                    {workspace.name}
                  </Select.Item>
                {/each}
              </Select.Group>
            </Select.Content>
          </Select.Root>
        </Field.Field>
      {/if}
      {#if teams.length > 0 || loadingTeams}
        <Field.Field class="gap-1">
          <Field.Label for="project-team">Team</Field.Label>
          <Select.Root
            type="single"
            value={teamId}
            onValueChange={(value) => (teamId = value ?? "")}
          >
            <Select.Trigger id="project-team" class="w-full">
              <span class="truncate">
                {teams.find((team) => team.id === teamId)?.name ??
                  (loadingTeams ? "Loading teams..." : "No team")}
              </span>
            </Select.Trigger>
            <Select.Content>
              <Select.Group>
                {#each teams as team (team.id)}
                  <Select.Item value={team.id} label={team.name}>
                    {team.name}
                  </Select.Item>
                {/each}
              </Select.Group>
            </Select.Content>
          </Select.Root>
        </Field.Field>
      {/if}
      <Field.Field class="gap-1">
        <Field.Label for="project-name">Name</Field.Label>
        <Input id="project-name" bind:value={name} placeholder="Project name" />
      </Field.Field>

      <Field.Field class="gap-1">
        <Field.Label for="project-manager">Manager</Field.Label>
        <Select.Root
          type="single"
          value={managerId}
          onValueChange={(v) => (managerId = v)}
        >
          <Select.Trigger id="project-manager" class="w-full">
            <span class="truncate"
              >{managerId ? userName(managerId) : "Select manager..."}</span
            >
          </Select.Trigger>
          <Select.Content>
            {#each users as user (user.id)}
              <Select.Item value={user.id} label={user.full_name}>
                {user.full_name}
              </Select.Item>
            {/each}
          </Select.Content>
        </Select.Root>
      </Field.Field>

      <Field.Field class="gap-1.5">
        <Field.Label>Color</Field.Label>
        <div class="flex flex-wrap gap-2">
          {#each COLORS as c (c)}
            <button
              type="button"
              class="size-7 rounded-full border-2 transition"
              class:border-base-content={color === c}
              style:background-color={c}
              onclick={() => (color = c)}
              aria-label="Select color {c}"
            ></button>
          {/each}
        </div>
      </Field.Field>

      <div class="grid grid-cols-2 gap-4">
        <Field.Field class="gap-1">
          <Field.Label for="project-start-date">Project start</Field.Label>
          <Input id="project-start-date" type="date" bind:value={startDate} />
        </Field.Field>
        {#if !isContinuous}
          <Field.Field class="gap-1">
            <Field.Label for="project-end-date">Project end</Field.Label>
            <Input id="project-end-date" type="date" bind:value={endDate} />
          </Field.Field>
        {:else}
          <p class="self-end pb-2 text-sm text-base-content/60">
            Ongoing project
          </p>
        {/if}
      </div>

      <label class="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          class="checkbox"
          checked={isContinuous}
          onchange={updateContinuous}
        />
        <span>Continuous project</span>
      </label>

      <Field.Field class="gap-1">
        <Field.Label for="project-description">Description</Field.Label>
        <Textarea
          id="project-description"
          bind:value={description}
          placeholder="Optional description"
          class="min-h-[80px]"
        />
      </Field.Field>
    </div>

    <Dialog.Footer>
      <Button variant="outline" onclick={() => (open = false)}>Cancel</Button>
      <Button disabled={saving} onclick={handleSave}>
        {saving ? "Saving..." : isEdit ? "Save Changes" : "Create Project"}
      </Button>
    </Dialog.Footer>
  </Dialog.Content>
</Dialog.Root>
