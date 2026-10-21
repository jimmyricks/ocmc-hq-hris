<script lang="ts">
  import { browser } from "$app/environment";
  import { goto } from "$app/navigation";
  import { refCache } from "$lib/task-manager/ref-cache.js";
  import { listFiltered, saveEntity } from "$lib/api/index.js";
  import { toast } from "$lib/notifications";
  import { workspaceApi } from "$lib/workspaces/api.js";
  import type {
    Project,
    Task,
    TaskAssignment,
    User,
  } from "$lib/task-manager/types.js";
  import { getToken, getUser } from "$lib/auth";
  import {
    stateBadge,
    formatDueDate,
    PRIORITY_META,
    taskState,
  } from "$lib/task-manager/utils.js";

  import * as Tabs from "$lib/components/ui/tabs/index.js";
  import * as Table from "$lib/components/ui/table/index.js";
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

  let tasks = $state<Task[]>([]);
  let assignments = $state<TaskAssignment[]>([]);
  let projects = $state<Project[]>([]);
  let users = $state<User[]>([]);
  let loading = $state(true);
  let error = $state("");
  let tab = $state("active");
  let detailOpen = $state(false);
  let detailTaskId = $state<string | null>(null);
  let canManageWorkspace = $state(false);
  let selectedProject = $state<Project | null>(null);
  let configOpen = $state(false);
  let membersOpen = $state(false);

  let activeTasks = $derived(
    tasks.filter((t) => {
      const s = taskState(t);
      return [
        "draft_assigned",
        "in_progress",
        "needs_revision",
        "for_review",
      ].includes(s);
    }),
  );
  let completedTasks = $derived(
    tasks.filter((t) => {
      const s = taskState(t);
      return ["approved", "closed"].includes(s);
    }),
  );

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
    load();
  });

  async function load() {
    loading = true;
    error = "";
    try {
      const user = getUser();
      if (!user) {
        goto("/login");
        return;
      }
      const [assignmentsRes, projectsRes, workspaceRes] = await Promise.all([
        listFiltered("task_assignment", [
          { field: "user_id", op: "eq", value: user.id },
        ]),
        refCache.getProjects(),
        workspaceApi.getContext().catch(() => null),
      ]);
      assignments = (assignmentsRes.data ?? []) as TaskAssignment[];
      projects = projectsRes;
      canManageWorkspace = workspaceRes?.can_manage ?? false;
      const taskIds = assignments.map((a) => a.task_id);
      if (taskIds.length === 0) {
        tasks = [];
        loading = false;
        return;
      }
      const tasksRes = await listFiltered("task", [
        { field: "id", op: "in", value: taskIds },
      ]);
      tasks = (tasksRes.data ?? []) as Task[];
    } catch (err: any) {
      error = err.message || "Failed to load tasks";
    } finally {
      loading = false;
    }
  }
</script>

<div class="flex flex-col gap-6">
  <div class="flex items-center justify-between">
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
        {#if !loading && activeTasks.length}
          <span class="ml-1 text-xs text-base-content/60"
            >{activeTasks.length}</span
          >
        {/if}
      </Tabs.Trigger>
      <Tabs.Trigger value="completed" class="gap-1.5">
        Completed
        {#if !loading && completedTasks.length}
          <span class="ml-1 text-xs text-base-content/60"
            >{completedTasks.length}</span
          >
        {/if}
      </Tabs.Trigger>
    </Tabs.List>

    {#each [{ value: "active", tasks: activeTasks }, { value: "completed", tasks: completedTasks }] as { value: tabValue, tasks: list } (tabValue)}
      <Tabs.Content value={tabValue} class="pt-4">
        <div class="border rounded-xl">
          <Table.Root>
            <Table.Header class="h-10 bg-base-200/50">
              <Table.Row>
                <Table.Head class="h-9 text-sm font-medium text-base-content/60"
                  >Task</Table.Head
                >
                <Table.Head class="h-9 text-sm font-medium text-base-content/60"
                  >Project</Table.Head
                >
                <Table.Head class="h-9 text-sm font-medium text-base-content/60"
                  >Priority</Table.Head
                >
                <Table.Head class="h-9 text-sm font-medium text-base-content/60"
                  >State</Table.Head
                >
                <Table.Head class="h-9 text-sm font-medium text-base-content/60"
                  >Due</Table.Head
                >
                <Table.Head class="h-9 w-10"></Table.Head>
              </Table.Row>
            </Table.Header>
            <Table.Body>
              {#if loading}
                {#each Array.from({ length: 4 }) as _, i (i)}
                  <Table.Row>
                    {#each Array.from({ length: 6 }) as _, j (j)}
                      <Table.Cell
                        ><Skeleton
                          class="h-4 w-full max-w-[6rem]"
                        /></Table.Cell
                      >
                    {/each}
                  </Table.Row>
                {/each}
              {:else if list.length === 0}
                <Table.Row>
                  <Table.Cell colspan={6} class="h-40">
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
                  </Table.Cell>
                </Table.Row>
              {:else}
                {#each list as task (task.id)}
                  {@const badge = stateBadge({
                    workflow_state: task.workflow_state,
                    status: task.status,
                  })}
                  {@const pmeta = PRIORITY_META[task.priority]}
                  {@const due = formatDueDate(task.due_date)}
                  {@const taskProject = projects.find(
                    (project) => project.id === task.project_id,
                  )}
                  <Table.Row
                    class="cursor-pointer hover:bg-base-200/40"
                    onclick={() => {
                      detailTaskId = task.id;
                      detailOpen = true;
                    }}
                  >
                    <Table.Cell class="max-w-[16rem]">
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
                    </Table.Cell>
                    <Table.Cell class="text-sm text-base-content/60"
                      >{projectName(task.project_id)}</Table.Cell
                    >
                    <Table.Cell>
                      <Badge
                        class="text-xs rounded-xl"
                        variant="outline"
                        style="border-color: {pmeta.color}; color: {pmeta.color};"
                      >
                        {pmeta.label}
                      </Badge>
                    </Table.Cell>
                    <Table.Cell>
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
                    </Table.Cell>
                    <Table.Cell>
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
                    </Table.Cell>
                    <Table.Cell onclick={(event) => event.stopPropagation()}>
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
                    </Table.Cell>
                  </Table.Row>
                {/each}
              {/if}
            </Table.Body>
          </Table.Root>
        </div>
      </Tabs.Content>
    {/each}
  </Tabs.Root>
</div>

<TaskDetailModal
  bind:open={detailOpen}
  taskId={detailTaskId}
  {projects}
  onTaskUpdated={load}
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
    {users}
    onChanged={load}
  />
{/if}
