<script lang="ts">
  import { browser } from "$app/environment";
  import { goto } from "$app/navigation";
  import { refCache } from "$lib/task-manager/ref-cache.js";
  import { saveEntity } from "$lib/api/index.js";
  import { toast } from "$lib/notifications";
  import { taskApi } from "$lib/task-manager/api.js";
  import type { Project, Task, User } from "$lib/task-manager/types.js";
  import { getToken } from "$lib/auth";
  import { useAppState } from "$lib/app-state.svelte.js";
  import Pagination from "$lib/components/pagination.svelte";
  import {
    stateBadge,
    formatDueDate,
    PRIORITY_META,
    taskState,
  } from "$lib/task-manager/utils.js";

  import * as Tabs from "$lib/components/ui/tabs/index.js";
  import { Button } from "$lib/components/ui/button/index.js";
  import { Badge } from "$lib/components/ui/badge/index.js";
  import * as Empty from "$lib/components/ui/empty/index.js";
  import { Skeleton } from "$lib/components/ui/skeleton/index.js";
  import * as DropdownMenu from "$lib/components/ui/dropdown-menu/index.js";
  import TaskDetailModal from "$lib/components/task-manager/task-detail-modal.svelte";
  import ProjectFormModal from "$lib/components/project-form-modal.svelte";
  import ProjectMembersModal from "$lib/components/project-members-modal.svelte";

  import ArrowRightIcon from "@lucide/svelte/icons/arrow-right";
  import AlertTriangleIcon from "@lucide/svelte/icons/alert-triangle";
  import InboxIcon from "@lucide/svelte/icons/inbox";
  import MoreVerticalIcon from "@lucide/svelte/icons/more-vertical";
  import SettingsIcon from "@lucide/svelte/icons/settings";
  import UserPlusIcon from "@lucide/svelte/icons/user-plus";
  import XIcon from "@lucide/svelte/icons/x";

  const appState = useAppState();
  let tasks = $state<Task[]>([]);
  let projects = $state<Project[]>([]);
  let users = $state<User[]>([]);
  let loading = $state(true);
  let error = $state("");
  let tab = $state("active");
  let tasksPageSize = $state(25);
  let tasksTotal = $state(0);
  let tasksPage = $state(appState.tablePage("my-tasks", "active"));
  let loadedTab = $state("");
  let detailOpen = $state(false);
  let detailTaskId = $state<string | null>(null);
  let canManageWorkspace = $state(false);
  let selectedProject = $state<Project | null>(null);
  let configOpen = $state(false);
  let membersOpen = $state(false);

  function projectName(id: string): string {
    return projects.find((p) => p.id === id)?.name ?? "—";
  }

  async function ensureUsers() {
    if (users.length) return;
    users = await refCache.getUsers().catch(() => [] as User[]);
  }

  async function configureProject(project: Project) {
    await ensureUsers();
    selectedProject = project;
    configOpen = true;
  }

  async function addMember(project: Project) {
    await ensureUsers();
    selectedProject = project;
    membersOpen = true;
  }

  async function closeProject(project: Project) {
    if (
      !confirm(`Close project "${project.name}"? This is a destructive action.`)
    )
      return;
    try {
      await saveEntity(
        "project",
        {
          ...project,
          status: "closed",
        },
        project.id,
      );
      toast.success("Project closed");
      await load();
    } catch (err: any) {
      toast.error(err.message || "Failed to close project");
    }
  }

  async function onProjectSaved(saved: Project) {
    projects = projects.map((project) =>
      project.id === saved.id ? saved : project,
    );
    await load();
  }

  $effect(() => {
    if (!browser) return;
    if (!getToken()) {
      goto("/login");
      return;
    }
    if (loadedTab !== tab) {
      loadedTab = tab;
      tasksPage = appState.tablePage("my-tasks", tab);
      void load();
    }
  });

  async function load() {
    loading = true;
    error = "";
    try {
      const [projectsRes, boot] = await Promise.all([
        refCache.getProjects(),
        appState.ensureBoot(),
      ]);
      projects = projectsRes;
      canManageWorkspace = Boolean(boot?.workspace_context?.can_manage);
      await loadTasks(tasksPage);
    } catch (err: any) {
      error = err.message || "Failed to load tasks";
    } finally {
      loading = false;
    }
  }

  async function loadTasks(targetPage = tasksPage) {
    try {
      const result = await taskApi.getMyTasksPage(
        tab === "completed" ? "completed" : "active",
        "",
        targetPage,
        tasksPageSize,
      );
      if (!result.items.length && result.total > 0 && targetPage > 1) {
        return loadTasks(Math.ceil(result.total / tasksPageSize));
      }
      tasks = result.items;
      tasksTotal = result.total;
      tasksPage = result.page;
      appState.rememberTablePage("my-tasks", tasksPage, tab);
    } catch (err: any) {
      error = err.message || "Failed to load tasks";
      tasks = [];
      tasksTotal = 0;
    }
  }

  function setTasksPage(targetPage: number) {
    tasksPage = targetPage;
    appState.rememberTablePage("my-tasks", targetPage, tab);
    void loadTasks(targetPage);
  }

  async function refreshTasks() {
    await loadTasks(tasksPage);
  }
</script>

<div class="flex flex-col gap-6">
  <div class="flex flex-wrap items-end justify-between gap-4">
    <h1 class="text-2xl font-bold tracking-tight">My Tasks</h1>
  </div>

  {#if error}
    <p class="rounded-md bg-error/10 p-3 text-sm text-error">
      {error}
    </p>
  {/if}

  <Tabs.Root bind:value={tab}>
    <Tabs.List class="grid w-full max-w-xs grid-cols-2">
      <Tabs.Trigger value="active" class="gap-1.5">
        Active
        {#if !loading && tab === "active" && tasksTotal}
          <span class="ml-1 text-xs text-base-content/60">{tasksTotal}</span>
        {/if}
      </Tabs.Trigger>
      <Tabs.Trigger value="completed" class="gap-1.5">
        Completed
        {#if !loading && tab === "completed" && tasksTotal}
          <span class="ml-1 text-xs text-base-content/60">{tasksTotal}</span>
        {/if}
      </Tabs.Trigger>
    </Tabs.List>

    {#each [{ value: "active" }, { value: "completed" }] as { value: tabValue } (tabValue)}
      <Tabs.Content value={tabValue} class="pt-4">
        <div
          class="overflow-hidden rounded-box border border-base-300 bg-base-100"
        >
          <table class="table table-zebra">
            <thead>
              <tr>
                <th>Task</th>
                <th>Project</th>
                <th>Priority</th>
                <th>State</th>
                <th>Due</th>
                <th class="w-10"></th>
              </tr>
            </thead>
            <tbody>
              {#if loading}
                {#each Array.from({ length: 4 }) as _, i (i)}
                  <tr>
                    {#each Array.from({ length: 6 }) as _, j (j)}
                      <td><Skeleton class="h-4 w-full max-w-[6rem]" /></td>
                    {/each}
                  </tr>
                {/each}
              {:else if tasks.length === 0}
                <tr>
                  <td colspan={6} class="h-40">
                    <Empty.Root>
                      <Empty.Media variant="icon">
                        <InboxIcon />
                      </Empty.Media>
                      <Empty.Header>
                        <Empty.Title>
                          {tabValue === "active"
                            ? "No active tasks"
                            : "No completed tasks"}
                        </Empty.Title>
                        <Empty.Description>
                          {tabValue === "active"
                            ? "Tasks assigned to you will appear here."
                            : "Approved and closed tasks will appear here."}
                        </Empty.Description>
                      </Empty.Header>
                    </Empty.Root>
                  </td>
                </tr>
              {:else}
                {#each tasks as task (task.id)}
                  {@const badge = stateBadge({
                    workflow_state: task.workflow_state,
                    status: task.status,
                  })}
                  {@const pmeta = PRIORITY_META[task.priority]}
                  {@const due = formatDueDate(task.due_date)}
                  {@const taskProject = projects.find(
                    (project) => project.id === task.project_id,
                  )}
                  <tr
                    class="cursor-pointer hover:bg-base-200/40"
                    onclick={() => {
                      detailTaskId = task.id;
                      detailOpen = true;
                    }}
                  >
                    <td class="max-w-[16rem]">
                      <div class="flex flex-col gap-0.5">
                        <span class="block w-full truncate text-sm font-medium"
                          >{task.title}</span
                        >
                        {#if task.task_key}
                          <span class="font-mono text-xs text-base-content/60"
                            >{task.task_key}</span
                          >
                        {/if}
                      </div>
                    </td>
                    <td class="text-sm text-base-content/60"
                      >{projectName(task.project_id)}</td
                    >
                    <td>
                      <Badge
                        class="text-xs rounded-xl"
                        variant="outline"
                        style="border-color: {pmeta.color}; color: {pmeta.color};"
                      >
                        {pmeta.label}
                      </Badge>
                    </td>
                    <td>
                      <Badge
                        variant={badge.variant}
                        class="gap-1 text-xs rounded-xl"
                      >
                        <span
                          class="size-1.5 rounded-full"
                          style:background-color={badge.color}
                        ></span>
                        {badge.label}
                      </Badge>
                    </td>
                    <td>
                      <div class="flex items-center gap-1.5 whitespace-nowrap">
                        {#if due?.isOverdue}
                          <AlertTriangleIcon class="size-3.5 text-error" />
                          <span class="text-sm text-error">{due.relative}</span>
                        {:else if task.due_date}
                          <span class="text-sm">{due?.relative}</span>
                        {:else}
                          <span class="text-sm text-base-content/60">—</span>
                        {/if}
                      </div>
                    </td>
                    <td onclick={(event) => event.stopPropagation()}>
                      {#if canManageWorkspace && taskProject}
                        <DropdownMenu.Root>
                          <DropdownMenu.Trigger>
                            <Button
                              variant="ghost"
                              size="sm"
                              icon
                              aria-label={`Project actions for ${taskProject.name}`}
                            >
                              <MoreVerticalIcon class="size-4" />
                            </Button>
                          </DropdownMenu.Trigger>
                          <DropdownMenu.Content class="w-48" align="end">
                            <DropdownMenu.Item
                              onclick={() => configureProject(taskProject)}
                            >
                              <SettingsIcon class="size-4" />
                              Configure Project
                            </DropdownMenu.Item>
                            <DropdownMenu.Item
                              onclick={() => addMember(taskProject)}
                            >
                              <UserPlusIcon class="size-4" />
                              Add Member
                            </DropdownMenu.Item>
                            <DropdownMenu.Separator />
                            <DropdownMenu.Item
                              onclick={() => closeProject(taskProject)}
                              class="text-error"
                            >
                              <XIcon class="size-4" />
                              Close Project
                            </DropdownMenu.Item>
                          </DropdownMenu.Content>
                        </DropdownMenu.Root>
                      {:else}
                        <ArrowRightIcon class="size-4 text-base-content/60" />
                      {/if}
                    </td>
                  </tr>
                {/each}
              {/if}
            </tbody>
          </table>
          {#if tabValue === tab}
            <Pagination
              page={tasksPage}
              pageSize={tasksPageSize}
              total={tasksTotal}
              {loading}
              pageSizeOptions={[10, 25, 50, 100]}
              onchange={setTasksPage}
              onpagesizechange={(size) => {
                tasksPageSize = size;
                setTasksPage(1);
              }}
            />
          {/if}
        </div>
      </Tabs.Content>
    {/each}
  </Tabs.Root>
</div>

<TaskDetailModal
  bind:open={detailOpen}
  taskId={detailTaskId}
  {projects}
  onTaskUpdated={refreshTasks}
/>

{#if selectedProject}
  <ProjectFormModal
    bind:open={configOpen}
    project={selectedProject}
    {users}
    onSaved={onProjectSaved}
  />
  <ProjectMembersModal
    bind:open={membersOpen}
    project={selectedProject}
    onChanged={refreshTasks}
  />
{/if}
