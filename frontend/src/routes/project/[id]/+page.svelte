<script lang="ts">
  import { page } from "$app/state";
  import { browser } from "$app/environment";
  import { goto } from "$app/navigation";
  import { toast } from "svelte-sonner";
  import { taskApi } from "$lib/task-manager/api.js";
  import { refCache } from "$lib/task-manager/ref-cache.js";
  import type {
    Project,
    ProjectMember,
    Task,
    TaskCategory,
    TaskType,
    User,
    WorkflowState,
  } from "$lib/task-manager/types.js";
  import { Button } from "$lib/components/ui/button/index.js";
  import { Input } from "$lib/components/ui/input/index.js";
  import { Badge } from "$lib/components/ui/badge/index.js";
  import * as DropdownMenu from "$lib/components/ui/dropdown-menu/index.js";
  import * as Select from "$lib/components/ui/select/index.js";
  import ProjectTaskTable, {
    type EditableField,
    type TaskCreateInput,
  } from "$lib/components/task-manager/project-task-table.svelte";
  import { taskState } from "$lib/task-manager/utils.js";
  import TaskDetailModal from "$lib/components/task-manager/task-detail-modal.svelte";
  import { workspaceApi } from "$lib/workspaces/api";
  import ProjectFormModal from "$lib/components/project-form-modal.svelte";
  import ProjectMembersModal from "$lib/components/project-members-modal.svelte";

  import SearchIcon from "@lucide/svelte/icons/search";
  import MoreVerticalIcon from "@lucide/svelte/icons/more-vertical";
  import SettingsIcon from "@lucide/svelte/icons/settings";
  import UserPlusIcon from "@lucide/svelte/icons/user-plus";
  import XIcon from "@lucide/svelte/icons/x";

  let projectId = $derived(page.params.id ?? "all");
  let projects = $state<Project[]>([]);
  let users = $state<User[]>([]);
  let taskTypes = $state<TaskType[]>([]);
  let taskCategories = $state<TaskCategory[]>([]);
  let tasks = $state<Task[]>([]);
  let members = $state<ProjectMember[]>([]);
  let loading = $state(true);
  let searchQuery = $state("");
  let stateFilter = $state<string>("all");
  let detailOpen = $state(false);
  let detailTaskId = $state<string | null>(null);
  let canManageWorkspace = $state(false);

  // Project config / members modals
  let configOpen = $state(false);
  let membersOpen = $state(false);

  const selectedProject = $derived(
    projectId === "all"
      ? {
          id: "all",
          name: "All Tasks",
          color: "#6b7280",
          icon: "layers",
          manager_id: "",
        }
      : projects.find((p) => p.id === projectId) || {
          id: projectId,
          name: browser ? projectId : "Loading...",
          color: "#6b7280",
          icon: "layers",
          manager_id: "",
        },
  );

  const STATE_FILTERS: { value: string; label: string }[] = [
    { value: "all", label: "All States" },
    { value: "draft_assigned", label: "Draft" },
    { value: "in_progress", label: "In Progress" },
    { value: "for_review", label: "For Review" },
    { value: "needs_revision", label: "Needs Revision" },
    { value: "approved", label: "Approved" },
    { value: "closed", label: "Closed" },
  ];
  const filteredTasks = $derived(
    tasks.filter((t) => {
      const q = searchQuery.toLowerCase();
      const matchesSearch = !q || t.title.toLowerCase().includes(q);
      const state = taskState(t);
      const matchesState = stateFilter === "all" || state === stateFilter;
      return matchesSearch && matchesState;
    }),
  );

  async function loadData() {
    loading = true;
    try {
      // Types are needed for inline task creation; categories and users load
      // from the shared cache when a detail view requests them.
      // Members are lazy-loaded only when a project is selected (needed for
      // task creation assignee filtering and the members modal).
      const [projectsRes, tasksRes, taskTypesRes, workspaceRes] =
        await Promise.all([
          refCache.getProjects(),
          taskApi.getTasksForProject(projectId),
          refCache.getTaskTypes().catch(() => [] as TaskType[]),
          workspaceApi.getContext().catch(() => null),
        ]);
      projects = projectsRes;
      tasks = tasksRes;
      taskTypes = taskTypesRes;
      canManageWorkspace = workspaceRes?.can_manage ?? false;
      // Categories and users are not needed until task details are opened.
      refCache
        .getTaskCategories()
        .then((c) => (taskCategories = c))
        .catch(() => {});
      refCache
        .getUsers()
        .then((u) => (users = u))
        .catch(() => {});
      // Members are only needed for a specific project (not "all") and only
      // when creating tasks or managing members — load lazily.
      if (projectId !== "all") {
        members = [];
      }
    } catch (err) {
      console.error("Failed to load project tasks:", err);
      tasks = [];
    } finally {
      loading = false;
    }
  }

  // Load project members only when the members panel needs them.
  $effect(() => {
    if (!browser || projectId === "all") return;
    if (membersOpen && members.length === 0) {
      taskApi
        .getProjectMembers(projectId)
        .then((m) => (members = m))
        .catch(() => {});
    }
  });

  function openTask(task: Task) {
    detailTaskId = task.id;
    detailOpen = true;
  }

  async function updateTaskCell(
    task: Task,
    field: EditableField,
    value: string | null,
  ) {
    const updated = { ...task, [field]: value } as Task;
    const saved = await taskApi.updateTask(updated);
    tasks = tasks.map((item) =>
      item.id === task.id ? (saved ?? updated) : item,
    );
  }

  async function createInlineTask(draft: TaskCreateInput) {
    const created = await taskApi.createTask(draft);
    tasks = [...tasks, created];
    toast.success("Task created");
  }

  function onTaskDeleted(id: string) {
    tasks = tasks.filter((t) => t.id !== id);
  }

  function configureProject() {
    configOpen = true;
  }

  function addMember() {
    membersOpen = true;
  }

  async function closeProject() {
    if (!selectedProject || projectId === "all") return;
    if (
      !confirm(
        `Close project "${selectedProject.name}"? This is a destructive action.`,
      )
    )
      return;
    try {
      await taskApi.updateTask({
        ...selectedProject,
        status: "closed",
      } as any);
      toast.success("Project closed");
      await loadData();
    } catch (err: any) {
      toast.error(err.message || "Failed to close project");
    }
  }

  async function onProjectSaved(saved: Project) {
    const exists = projects.some((p) => p.id === saved.id);
    projects = exists
      ? projects.map((p) => (p.id === saved.id ? saved : p))
      : [...projects, saved];
    if (!exists) {
      goto(`/project/${saved.id}`);
    } else {
      await loadData();
    }
  }

  $effect(() => {
    if (!browser) return;
    loadData();
  });
</script>

<div class="flex flex-col gap-6">
  <header
    class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between"
  >
    <div class="flex items-center gap-2.5">
      <span
        class="size-3 rounded-full"
        style:background-color={selectedProject.color}
      ></span>
      <h1 class="text-2xl font-medium tracking-tight">
        {selectedProject.name}
      </h1>
      {#if projectId !== "all" && members.length > 0}
        <Badge variant="secondary" class="gap-1">
          {members.length}
          {members.length === 1 ? "member" : "members"}
        </Badge>
      {/if}
    </div>
    <div class="flex items-center gap-2">
      {#if browser && projectId !== "all" && canManageWorkspace}
        <DropdownMenu.Root>
          <DropdownMenu.Trigger>
            <Button variant="outline" class="h-9 gap-1.5 px-2">
              <MoreVerticalIcon class="size-4" />
            </Button>
          </DropdownMenu.Trigger>
          <DropdownMenu.Content class="w-48" align="end">
            <DropdownMenu.Item onclick={configureProject}>
              <SettingsIcon class="size-4" />
              Configure Project
            </DropdownMenu.Item>
            <DropdownMenu.Item onclick={addMember}>
              <UserPlusIcon class="size-4" />
              Add Member
            </DropdownMenu.Item>
            <DropdownMenu.Separator />
            <DropdownMenu.Item onclick={closeProject} class="text-destructive">
              <XIcon class="size-4" />
              Close Project
            </DropdownMenu.Item>
          </DropdownMenu.Content>
        </DropdownMenu.Root>
      {/if}
    </div>
  </header>

  <!-- Filters -->
  <div class="flex flex-col gap-3 sm:flex-row sm:items-center">
    <div class="relative flex-1">
      <SearchIcon
        class="absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
      />
      <Input
        type="search"
        placeholder="Search tasks..."
        bind:value={searchQuery}
        class="h-9 w-full pl-9 sm:max-w-xs"
      />
    </div>
    <Select.Root
      type="single"
      value={stateFilter}
      onValueChange={(v) => (stateFilter = v)}
    >
      <Select.Trigger class="h-9 w-full sm:w-44">
        {STATE_FILTERS.find((f) => f.value === stateFilter)?.label ??
          "All States"}
      </Select.Trigger>
      <Select.Content>
        {#each STATE_FILTERS as f (f.value)}
          <Select.Item value={f.value} label={f.label}>{f.label}</Select.Item>
        {/each}
      </Select.Content>
    </Select.Root>
  </div>
  <ProjectTaskTable
    tasks={filteredTasks}
    {loading}
    {taskTypes}
    defaultProjectId={projectId !== "all" ? projectId : (projects[0]?.id ?? "")}
    canEdit={canManageWorkspace}
    canCreate={canManageWorkspace &&
      (projectId !== "all" || projects.length > 0)}
    onCreate={createInlineTask}
    onUpdate={updateTaskCell}
    onOpen={openTask}
  />
</div>

<TaskDetailModal
  bind:open={detailOpen}
  taskId={detailTaskId}
  {projects}
  {taskTypes}
  {taskCategories}
  {members}
  {users}
  onTaskUpdated={loadData}
  {onTaskDeleted}
/>

{#if projectId !== "all"}
  <ProjectFormModal
    bind:open={configOpen}
    project={selectedProject}
    {users}
    onSaved={onProjectSaved}
  />
  <ProjectMembersModal
    bind:open={membersOpen}
    project={selectedProject}
    {users}
    onChanged={loadData}
  />
{/if}
