<script lang="ts">
  import { browser } from "$app/environment";
  import { goto } from "$app/navigation";
  import { taskApi } from "$lib/task-manager/api.js";
  import { refCache } from "$lib/task-manager/ref-cache.js";
  import { listFiltered } from "$lib/api/index.js";
  import type {
    Project,
    Task,
    TaskAssignment,
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
  import TaskDetailModal from "$lib/components/task-manager/task-detail-modal.svelte";

  import ArrowRightIcon from "@lucide/svelte/icons/arrow-right";
  import AlertTriangleIcon from "@lucide/svelte/icons/alert-triangle";
  import InboxIcon from "@lucide/svelte/icons/inbox";
  import CheckSquareIcon from "@lucide/svelte/icons/check-square";

  let tasks = $state<Task[]>([]);
  let assignments = $state<TaskAssignment[]>([]);
  let projects = $state<Project[]>([]);
  let loading = $state(true);
  let error = $state("");
  let tab = $state("active");
  let detailOpen = $state(false);
  let detailTaskId = $state<string | null>(null);

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
      const [assignmentsRes, projectsRes] = await Promise.all([
        listFiltered("task_assignment", [
          { field: "user_id", op: "eq", value: user.id },
        ]),
        refCache.getProjects(),
      ]);
      assignments = (assignmentsRes.data ?? []) as TaskAssignment[];
      projects = projectsRes;
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
    <p class="rounded-md bg-destructive/10 p-3 text-sm text-destructive">
      {error}
    </p>
  {/if}

  <Tabs.Root bind:value={tab}>
    <Tabs.List class="grid w-full max-w-xs grid-cols-2">
      <Tabs.Trigger value="active" class="gap-1.5">
        Active
        {#if !loading && activeTasks.length}
          <span class="ml-1 text-xs text-muted-foreground"
            >{activeTasks.length}</span
          >
        {/if}
      </Tabs.Trigger>
      <Tabs.Trigger value="completed" class="gap-1.5">
        Completed
        {#if !loading && completedTasks.length}
          <span class="ml-1 text-xs text-muted-foreground"
            >{completedTasks.length}</span
          >
        {/if}
      </Tabs.Trigger>
    </Tabs.List>

    {#each [{ value: "active", tasks: activeTasks }, { value: "completed", tasks: completedTasks }] as { value: tabValue, tasks: list } (tabValue)}
      <Tabs.Content value={tabValue} class="pt-4">
        <div class="border rounded-xl">
          <Table.Root>
            <Table.Header class="h-10 bg-muted/50">
              <Table.Row>
                <Table.Head
                  class="h-9 text-sm font-medium text-muted-foreground"
                  >Task</Table.Head
                >
                <Table.Head
                  class="h-9 text-sm font-medium text-muted-foreground"
                  >Project</Table.Head
                >
                <Table.Head
                  class="h-9 text-sm font-medium text-muted-foreground"
                  >Priority</Table.Head
                >
                <Table.Head
                  class="h-9 text-sm font-medium text-muted-foreground"
                  >State</Table.Head
                >
                <Table.Head
                  class="h-9 text-sm font-medium text-muted-foreground"
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
                  <Table.Row
                    class="cursor-pointer hover:bg-muted/40"
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
                          <span class="font-mono text-xs text-muted-foreground"
                            >{task.task_key}</span
                          >
                        {/if}
                      </div>
                    </Table.Cell>
                    <Table.Cell class="text-sm text-muted-foreground"
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
                          <AlertTriangleIcon
                            class="size-3.5 text-destructive"
                          />
                          <span class="text-sm text-destructive"
                            >{due.relative}</span
                          >
                        {:else if task.due_date}
                          <span class="text-sm">{due?.relative}</span>
                        {:else}
                          <span class="text-sm text-muted-foreground">—</span>
                        {/if}
                      </div>
                    </Table.Cell>
                    <Table.Cell>
                      <ArrowRightIcon class="size-4 text-muted-foreground" />
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
