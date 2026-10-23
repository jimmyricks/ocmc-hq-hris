<script lang="ts">
  import { page } from "$app/state";
  import { browser } from "$app/environment";
  import { goto } from "$app/navigation";
  import { toast } from "$lib/notifications";
  import { taskApi } from "$lib/task-manager/api.js";
  import { saveEntity } from "$lib/api/index.js";
  import { refCache } from "$lib/task-manager/ref-cache.js";
  import { userApi } from "$lib/users/api.js";
  import type {
    Project,
    ProjectMember,
    Task,
    TaskCategory,
    TaskSummary,
    TaskType,
    User,
    WorkflowState,
  } from "$lib/task-manager/types.js";
  import { Button } from "$lib/components/ui/button/index.js";
  import { Input } from "$lib/components/ui/input/index.js";
  import { Badge } from "$lib/components/ui/badge/index.js";
  import * as DropdownMenu from "$lib/components/ui/dropdown-menu/index.js";
  import * as Select from "$lib/components/ui/select/index.js";
  import ProjectTaskTable from "$lib/components/task-manager/project-task-table.svelte";
  import TaskDetailModal from "$lib/components/task-manager/task-detail-modal.svelte";
  import { useAppState } from "$lib/app-state.svelte.js";
  import ProjectFormModal from "$lib/components/project-form-modal.svelte";
  import ProjectMembersModal from "$lib/components/project-members-modal.svelte";

  import SearchIcon from "@lucide/svelte/icons/search";
  import MoreVerticalIcon from "@lucide/svelte/icons/more-vertical";
  import SettingsIcon from "@lucide/svelte/icons/settings";
  import UserPlusIcon from "@lucide/svelte/icons/user-plus";
  import XIcon from "@lucide/svelte/icons/x";

  const appState = useAppState();
  let projectId = $derived(page.params.id ?? "all");
  let projects = $state<Project[]>([]);
  let users = $state<User[]>([]);
  let taskTypes = $state<TaskType[]>([]);
  let taskCategories = $state<TaskCategory[]>([]);
  let tasks = $state<Task[]>([]);
  let taskSummaries = $state<Record<string, TaskSummary>>({});
  let members = $state<ProjectMember[]>([]);
  let loading = $state(true);
  let searchQuery = $state("");
  let appliedSearch = $state("");
  let searchTimer: ReturnType<typeof setTimeout> | undefined;
  let stateFilter = $state<string>("all");
  let tasksPage = $state(1);
  let tasksPageSize = $state(25);
  let tasksTotal = $state(0);
  let loadedProjectId = $state("");
  let detailOpen = $state(false);
  let detailTaskId = $state<string | null>(null);
  let newTaskDraft = $state<Task | null>(null);
  let canManageWorkspace = $state(false);

  // Project config / members modals
  let configOpen = $state(false);
  let membersOpen = $state(false);

  const selectedProject = $derived(
    projectId === "all"
      ? {
          id: "all",
          name: "All Tasks",
          color: "var(--color-base-content)",
          icon: "layers",
          manager_id: "",
        }
      : projects.find((p) => p.id === projectId) || {
          id: projectId,
          name: browser ? projectId : "Loading...",
          color: "var(--color-base-content)",
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
  async function loadTasks(targetPage = tasksPage) {
    loading = true;
    try {
      const result = await taskApi.getTasksForProjectPage(
        projectId,
        targetPage,
        tasksPageSize,
        appliedSearch,
        stateFilter,
      );
      if (!result.items.length && result.total > 0 && targetPage > 1) {
        return loadTasks(Math.ceil(result.total / tasksPageSize));
      }
      tasks = result.items;
      tasksTotal = result.total;
      tasksPage = result.page;
      appState.rememberTablePage("project-tasks", tasksPage, projectId);
      taskSummaries = await taskApi
        .getTaskSummaries(tasks.map((t) => t.id))
        .catch(() => ({}));
    } catch (err) {
      console.error("Failed to load project tasks:", err);
      tasks = [];
      taskSummaries = {};
      tasksTotal = 0;
    } finally {
      loading = false;
    }
  }

  async function loadData() {
    loading = true;
    try {
      // Types are needed for inline task creation; categories and users load
      // from the shared cache when a detail view requests them.
      const [projectsRes, taskTypesRes, boot] = await Promise.all([
        refCache.getProjects(),
        refCache.getTaskTypes().catch(() => [] as TaskType[]),
        appState.ensureBoot(),
      ]);
      projects = projectsRes;
      taskTypes = taskTypesRes;
      canManageWorkspace = Boolean(boot?.workspace_context?.can_manage);
      // Categories and users are not needed until task details are opened.
      refCache
        .getTaskCategories()
        .then((c) => (taskCategories = c))
        .catch(() => {});
      // Full directory is supervisor-only; members get the project-scoped list.
      if (canManageWorkspace) {
        refCache
          .getUsers()
          .then((u) => (users = u))
          .catch(() => {});
      } else if (projectId !== "all") {
        userApi
          .lookup({ projectId, pageSize: 100 })
          .then((u) => (users = u))
          .catch(() => {});
      }
      await loadTasks(tasksPage);
    } catch (err) {
      console.error("Failed to load project tasks:", err);
      tasks = [];
    } finally {
      loading = false;
    }
  }

  function setTasksPage(targetPage: number) {
    tasksPage = targetPage;
    appState.rememberTablePage("project-tasks", targetPage, projectId);
    void loadTasks(targetPage);
  }

  function queueSearch() {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
      appliedSearch = searchQuery.trim();
      setTasksPage(1);
    }, 300);
  }

  function setStateFilter(value: string) {
    stateFilter = value;
    setTasksPage(1);
  }

  function openTask(task: Task) {
    newTaskDraft = null;
    detailTaskId = task.id;
    detailOpen = true;
  }

  function addTask() {
    const defaultProject =
      projectId !== "all" ? projectId : (projects[0]?.id ?? "");
    if (!defaultProject) {
      toast.error("Create a project before adding tasks");
      return;
    }
    detailTaskId = null;
    newTaskDraft = {
      id: "",
      project_id: defaultProject,
      task_type_id: "",
      title: "",
      status: "draft",
      priority: "medium",
    };
    detailOpen = true;
  }

  function onTaskCreated() {
    newTaskDraft = null;
    void loadTasks(tasksPage);
  }

  function onTaskDeleted(id: string) {
    tasks = tasks.filter((t) => t.id !== id);
    tasksTotal = Math.max(0, tasksTotal - 1);
    void loadTasks(tasksPage);
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
      await saveEntity(
        "project",
        {
          ...selectedProject,
          status: "closed",
        },
        selectedProject.id,
      );
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
    if (!browser || loadedProjectId === projectId) return;
    loadedProjectId = projectId;
    tasksPage = appState.tablePage("project-tasks", projectId);
    void loadData();
  });
</script>

<div class="flex flex-col gap-6">
  <header class="flex flex-wrap items-end justify-between gap-4">
    <div class="flex items-center gap-2.5">
      <span
        class="size-3 rounded-full"
        style:background-color={selectedProject.color}
      ></span>
      <h1 class="text-2xl font-bold tracking-tight">
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
            <Button variant="outline" size="md" icon class="gap-1.5">
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
            <DropdownMenu.Item onclick={closeProject} class="text-error">
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
        class="absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-base-content/60"
      />
      <Input
        type="search"
        placeholder="Search tasks..."
        bind:value={searchQuery}
        size="md"
        class="w-full pl-9 sm:max-w-xs"
        oninput={queueSearch}
      />
    </div>
    <Select.Root
      type="single"
      value={stateFilter}
      onValueChange={setStateFilter}
    >
      <Select.Trigger size="md" class="w-full sm:w-44">
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
    {tasks}
    {loading}
    {taskTypes}
    summaries={taskSummaries}
    canCreate={canManageWorkspace &&
      (projectId !== "all" || projects.length > 0)}
    onAddTask={addTask}
    onOpen={openTask}
    page={tasksPage}
    pageSize={tasksPageSize}
    total={tasksTotal}
    onPageChange={setTasksPage}
    onPageSizeChange={(size) => {
      tasksPageSize = size;
      setTasksPage(1);
    }}
  />
</div>

<TaskDetailModal
  bind:open={detailOpen}
  presentation="drawer"
  taskId={detailTaskId}
  newTask={newTaskDraft}
  {projects}
  {taskTypes}
  {taskCategories}
  {members}
  {users}
  onTaskUpdated={loadData}
  {onTaskCreated}
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
    onChanged={(updatedMembers) => (members = updatedMembers)}
  />
{/if}
