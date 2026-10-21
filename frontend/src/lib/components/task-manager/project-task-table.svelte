<script lang="ts">
  import { toast } from "$lib/notifications";
  import * as Empty from "$lib/components/ui/empty/index.js";
  import { Badge } from "$lib/components/ui/badge/index.js";
  import { Button } from "$lib/components/ui/button/index.js";
  import { Input } from "$lib/components/ui/input/index.js";
  import { Skeleton } from "$lib/components/ui/skeleton/index.js";
  import * as Select from "$lib/components/ui/select/index.js";
  import type { Priority, Task, TaskType } from "$lib/task-manager/types.js";
  import {
    formatDueDate,
    PRIORITY_META,
    stateBadge,
  } from "$lib/task-manager/utils.js";

  import AlertTriangleIcon from "@lucide/svelte/icons/alert-triangle";
  import ArrowUpRightIcon from "@lucide/svelte/icons/arrow-up-right";
  import PlusIcon from "@lucide/svelte/icons/plus";

  export type TaskCreateInput = {
    project_id: string;
    task_type_id: string;
    title: string;
    priority: Priority;
    due_date?: string;
    description?: string;
  };

  type Props = {
    tasks: Task[];
    loading: boolean;
    taskTypes: TaskType[];
    defaultProjectId: string;
    canCreate: boolean;
    onCreate: (task: TaskCreateInput) => Promise<void>;
    onOpen: (task: Task) => void;
  };

  let {
    tasks,
    loading,
    taskTypes,
    defaultProjectId,
    canCreate,
    onCreate,
    onOpen,
  }: Props = $props();

  let newTask = $state<TaskCreateInput | null>(null);
  let dueDateInput = $state("");
  let creating = $state(false);
  const priorityOptions = Object.entries(PRIORITY_META).map(
    ([value, priority]) => ({ value, label: priority.label }),
  );
  function beginCreate() {
    if (!canCreate || !defaultProjectId) {
      toast.error("Create a project before adding tasks");
      return;
    }
    if (taskTypes.length === 0) {
      toast.error("No task types are available. Check the backend and retry.");
      return;
    }
    dueDateInput = "";
    newTask = {
      project_id: defaultProjectId,
      task_type_id: taskTypes[0].id,
      title: "",
      priority: "medium",
    };
  }

  async function createTask() {
    if (!newTask || creating) return;
    const draft = {
      ...newTask,
      title: newTask.title.trim(),
      due_date: dueDateInput ? `${dueDateInput}T00:00:00` : undefined,
    };
    if (!draft.title || !draft.task_type_id) return;

    creating = true;
    try {
      await onCreate(draft);
      newTask = null;
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : "Couldn't create task",
      );
    } finally {
      creating = false;
    }
  }

  function handleRowKeydown(event: KeyboardEvent, task: Task) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onOpen(task);
    }
  }
</script>

<section class="task-table-panel">
  <div class="task-table-toolbar">
    <p class="text-xs text-base-content/60">
      Select a task to view its details or submit assigned work.
    </p>
    <Button onclick={beginCreate} disabled={loading || !canCreate}>
      <PlusIcon data-icon="inline-start" />
      New Task
    </Button>
  </div>

  <div class="task-table-scroll">
    <table class="table table-zebra task-table">
      <thead>
        <tr>
          <th>Task</th>
          <th>Type</th>
          <th>Priority</th>
          <th>State</th>
          <th>Due</th>
          <th class="details-column"><span class="sr-only">Details</span></th>
        </tr>
      </thead>
      <tbody>
        {#if loading}
          {#each Array.from({ length: 5 }) as _, rowIndex (rowIndex)}
            <tr>
              {#each Array.from({ length: 6 }) as _, columnIndex (columnIndex)}
                <td><Skeleton class="h-4 w-full max-w-32" /></td>
              {/each}
            </tr>
          {/each}
        {:else}
          {#if newTask}
            <tr class="new-task-row">
              <td class="task-title-cell">
                <Input
                  bind:value={newTask.title}
                  placeholder="New task title"
                  aria-label="New task title"
                  size="sm"
                  autofocus
                />
              </td>
              <td>
                <Select.Root
                  type="single"
                  value={newTask.task_type_id}
                  onValueChange={(value) => {
                    if (newTask) newTask.task_type_id = value;
                  }}
                >
                  <Select.Trigger size="md">
                    {taskTypes.find((type) => type.id === newTask?.task_type_id)
                      ?.name ?? "Choose type"}
                  </Select.Trigger>
                  <Select.Content portal>
                    <Select.Group>
                      {#each taskTypes as type (type.id)}
                        <Select.Item value={type.id} label={type.name}>
                          {type.name}
                        </Select.Item>
                      {/each}
                    </Select.Group>
                  </Select.Content>
                </Select.Root>
              </td>
              <td>
                <Select.Root
                  type="single"
                  value={newTask.priority}
                  onValueChange={(value) => {
                    if (newTask) newTask.priority = value as Priority;
                  }}
                >
                  <Select.Trigger size="md">
                    {PRIORITY_META[newTask.priority].label}
                  </Select.Trigger>
                  <Select.Content portal>
                    <Select.Group>
                      {#each priorityOptions as option (option.value)}
                        <Select.Item value={option.value} label={option.label}>
                          {option.label}
                        </Select.Item>
                      {/each}
                    </Select.Group>
                  </Select.Content>
                </Select.Root>
              </td>
              <td><Badge variant="outline">Pending</Badge></td>
              <td>
                <Input
                  type="date"
                  aria-label="Due date"
                  size="sm"
                  bind:value={dueDateInput}
                />
              </td>
              <td class="details-column">
                <div class="flex items-center gap-1">
                  <Button
                    size="sm"
                    onclick={createTask}
                    disabled={creating || !newTask.title.trim()}
                  >
                    {creating ? "Saving…" : "Create"}
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onclick={() => (newTask = null)}
                    disabled={creating}
                  >
                    Cancel
                  </Button>
                </div>
              </td>
            </tr>
          {/if}

          {#if tasks.length === 0 && !newTask}
            <tr>
              <td colspan={6} class="empty-cell">
                <Empty.Root>
                  <Empty.Media variant="icon">
                    <PlusIcon />
                  </Empty.Media>
                  <Empty.Header>
                    <Empty.Title>No tasks yet</Empty.Title>
                    <Empty.Description>
                      Start with a row and fill in the cells.
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
              {@const priority = PRIORITY_META[task.priority]}
              {@const due = formatDueDate(task.due_date)}
              <tr
                class="task-data-row"
                role="button"
                tabindex="0"
                aria-label="Open task details: {task.title}"
                onclick={() => onOpen(task)}
                onkeydown={(event) => handleRowKeydown(event, task)}
              >
                <td class="task-title-cell">
                  <span class="block truncate font-medium">{task.title}</span>
                  {#if task.task_key}
                    <span class="font-mono text-xs text-base-content/60">
                      {task.task_key}
                    </span>
                  {/if}
                </td>
                <td>
                  {taskTypes.find((type) => type.id === task.task_type_id)
                    ?.name ?? "—"}
                </td>
                <td>
                  <Badge
                    variant="outline"
                    style="border-color: {priority.color}; color: {priority.color}"
                  >
                    {priority.label}
                  </Badge>
                </td>
                <td>
                  <Badge variant={badge.variant} class="gap-1">
                    <span
                      class="size-1.5 rounded-full"
                      style:background-color={badge.color}
                    ></span>
                    {badge.label}
                  </Badge>
                </td>
                <td>
                  {#if due?.isOverdue}
                    <span class="inline-flex items-center gap-1 text-error">
                      <AlertTriangleIcon class="size-3.5" />
                      {due.relative}
                    </span>
                  {:else if task.due_date}
                    <span>{due?.relative}</span>
                  {:else}
                    <span class="text-base-content/60">—</span>
                  {/if}
                </td>
                <td class="details-column">
                  <ArrowUpRightIcon
                    class="size-4 text-base-content/60"
                    aria-hidden="true"
                  />
                </td>
              </tr>
            {/each}
          {/if}
        {/if}
      </tbody>
    </table>
  </div>
</section>

<style>
  .task-table-panel {
    overflow: hidden;
    border: 1px solid var(--color-base-300);
    border-radius: var(--radius-box);
    background: var(--color-base-100);
  }

  .task-table-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    border-bottom: 1px solid var(--color-base-300);
    padding: 0.75rem 1rem;
  }

  .task-table-scroll {
    overflow-x: auto;
  }

  .task-table {
    width: 100%;
    min-width: 1160px;
    border-collapse: collapse;
    text-align: left;
    font-size: 0.875rem;
  }

  .task-table th {
    height: 2.5rem;
    padding: 0 1rem;
    background: var(--color-base-200);
    color: color-mix(in oklab, var(--color-base-content) 62%, transparent);
    font-size: 0.75rem;
    font-weight: 600;
  }

  .task-table td {
    height: 3.75rem;
    border-top: 1px solid var(--color-base-300);
    padding: 0.5rem 0.75rem;
    vertical-align: middle;
  }

  .task-data-row:hover {
    background: color-mix(in oklab, var(--color-base-200) 55%, transparent);
  }

  .task-data-row {
    cursor: pointer;
  }

  .task-data-row:focus-visible {
    outline: 2px solid var(--color-primary);
    outline-offset: -2px;
  }

  .new-task-row {
    background: color-mix(
      in oklab,
      var(--color-primary) 45%,
      var(--color-base-100)
    );
  }

  .task-title-cell {
    min-width: 13rem;
    max-width: 20rem;
  }

  .details-column {
    width: 1%;
    white-space: nowrap;
  }

  .empty-cell {
    padding: 2rem 1rem !important;
  }

  @media (max-width: 640px) {
    .task-table-toolbar {
      align-items: flex-start;
      flex-direction: column;
    }

    .task-table {
      min-width: 1080px;
    }
  }
</style>
