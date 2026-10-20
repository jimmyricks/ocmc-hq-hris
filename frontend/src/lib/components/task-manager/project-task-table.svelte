<script lang="ts">
  import { toast } from "$lib/notifications";
  import * as Empty from "$lib/components/native/empty/index.js";
  import { Badge } from "$lib/components/native/badge/index.js";
  import { Button } from "$lib/components/native/button/index.js";
  import { Input } from "$lib/components/native/input/index.js";
  import { Skeleton } from "$lib/components/native/skeleton/index.js";
  import * as Select from "$lib/components/native/select/index.js";
  import type { Priority, Task, TaskType } from "$lib/task-manager/types.js";
  import {
    formatDueDate,
    PRIORITY_META,
    stateBadge,
  } from "$lib/task-manager/utils.js";

  import AlertTriangleIcon from "@lucide/svelte/icons/alert-triangle";
  import MoreVerticalIcon from "@lucide/svelte/icons/more-vertical";
  import PlusIcon from "@lucide/svelte/icons/plus";

  export type EditableField =
    | "title"
    | "task_type_id"
    | "priority"
    | "due_date"
    | "planned_start_at"
    | "planned_end_at";
  export type TaskCreateInput = {
    project_id: string;
    task_type_id: string;
    title: string;
    priority: Priority;
    due_date?: string;
    planned_start_at?: string;
    planned_end_at?: string;
    description?: string;
  };

  type Props = {
    tasks: Task[];
    loading: boolean;
    taskTypes: TaskType[];
    defaultProjectId: string;
    canEdit: boolean;
    canCreate: boolean;
    onCreate: (task: TaskCreateInput) => Promise<void>;
    onUpdate: (
      task: Task,
      field: EditableField,
      value: string | null,
    ) => Promise<void>;
    onOpen: (task: Task) => void;
  };

  let {
    tasks,
    loading,
    taskTypes,
    defaultProjectId,
    canEdit,
    canCreate,
    onCreate,
    onUpdate,
    onOpen,
  }: Props = $props();

  let newTask = $state<TaskCreateInput | null>(null);
  let creating = $state(false);
  let editingCell = $state<{
    taskId: string;
    field: EditableField;
  } | null>(null);
  let cellDraft = $state("");
  let savingCell = $state(false);

  const priorityOptions = Object.entries(PRIORITY_META).map(
    ([value, priority]) => ({ value, label: priority.label }),
  );
  const taskTypeOptions = $derived(
    taskTypes.map((type) => ({ value: type.id, label: type.name })),
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
    newTask = {
      project_id: defaultProjectId,
      task_type_id: taskTypes[0].id,
      title: "",
      priority: "medium",
    };
  }

  function setNewTaskDate(
    field: "due_date" | "planned_start_at" | "planned_end_at",
    value: string,
  ) {
    if (!newTask) return;
    newTask[field] = value ? `${value}T00:00:00` : undefined;
  }

  function dateLabel(value?: string) {
    if (!value) return "Set date";
    return new Date(value).toLocaleDateString("en-PH", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  }

  async function createTask() {
    if (!newTask || creating) return;
    const draft = { ...newTask, title: newTask.title.trim() };
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

  function startEditing(task: Task, field: EditableField) {
    if (!canEdit) return;
    editingCell = { taskId: task.id, field };
    if (
      field === "due_date" ||
      field === "planned_start_at" ||
      field === "planned_end_at"
    ) {
      cellDraft = task[field]?.slice(0, 10) ?? "";
    } else {
      cellDraft = String(task[field] ?? "");
    }
  }

  function cancelEditing() {
    editingCell = null;
    cellDraft = "";
  }

  function isEditing(task: Task, field: EditableField) {
    return editingCell?.taskId === task.id && editingCell.field === field;
  }

  async function saveCell(task: Task, field: EditableField, value = cellDraft) {
    if (
      editingCell?.taskId !== task.id ||
      editingCell.field !== field ||
      savingCell
    )
      return;
    if (field === "title" && !value.trim()) {
      toast.error("Task title cannot be empty");
      return;
    }

    const nextValue =
      field === "due_date" ||
      field === "planned_start_at" ||
      field === "planned_end_at"
        ? value
          ? `${value}T00:00:00`
          : null
        : value.trim();

    savingCell = true;
    try {
      await onUpdate(task, field, nextValue);
      cancelEditing();
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : "Couldn't save cell",
      );
    } finally {
      savingCell = false;
    }
  }

  function handleEditorKeydown(event: KeyboardEvent) {
    if (event.key === "Escape") {
      event.preventDefault();
      cancelEditing();
    } else if (event.key === "Enter") {
      event.preventDefault();
      const task = tasks.find((item) => item.id === editingCell?.taskId);
      if (
        task &&
        editingCell &&
        editingCell.field !== "task_type_id" &&
        editingCell.field !== "priority"
      ) {
        void saveCell(task, editingCell.field);
      }
    }
  }

  async function updateChoice(
    task: Task,
    field: "task_type_id" | "priority",
    value: string,
  ) {
    if (!canEdit) return;
    try {
      await onUpdate(task, field, value);
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : "Couldn't save cell",
      );
    }
  }
</script>

<section class="task-table-panel">
  <div class="task-table-toolbar">
    <p class="text-xs text-muted-foreground">
      {canEdit
        ? "Click a title or date to edit. Choose a type or priority directly."
        : "Open a task to view details or submit assigned work."}
    </p>
    <Button onclick={beginCreate} disabled={loading || !canCreate}>
      <PlusIcon data-icon="inline-start" />
      New Task
    </Button>
  </div>

  <div class="task-table-scroll">
    <table class="task-table">
      <thead>
        <tr>
          <th>Task</th>
          <th>Type</th>
          <th>Priority</th>
          <th>State</th>
          <th>Planned start</th>
          <th>Planned end</th>
          <th>Due</th>
          <th class="details-column"><span class="sr-only">Details</span></th>
        </tr>
      </thead>
      <tbody>
        {#if loading}
          {#each Array.from({ length: 5 }) as _, rowIndex (rowIndex)}
            <tr>
              {#each Array.from({ length: 8 }) as _, columnIndex (columnIndex)}
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
                  class="h-9"
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
                  <Select.Trigger class="task-table-select">
                    {taskTypes.find((type) => type.id === newTask?.task_type_id)
                      ?.name ?? "Choose type"}
                  </Select.Trigger>
                  <Select.Content>
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
                  <Select.Trigger class="task-table-select">
                    {PRIORITY_META[newTask.priority].label}
                  </Select.Trigger>
                  <Select.Content>
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
                  aria-label="Planned start date"
                  class="h-9"
                  value={newTask.planned_start_at?.slice(0, 10) ?? ""}
                  oninput={(event) =>
                    setNewTaskDate(
                      "planned_start_at",
                      event.currentTarget.value,
                    )}
                />
              </td>
              <td>
                <Input
                  type="date"
                  aria-label="Planned end date"
                  class="h-9"
                  value={newTask.planned_end_at?.slice(0, 10) ?? ""}
                  oninput={(event) =>
                    setNewTaskDate("planned_end_at", event.currentTarget.value)}
                />
              </td>
              <td>
                <Input
                  type="date"
                  aria-label="Due date"
                  class="h-9"
                  value={newTask.due_date?.slice(0, 10) ?? ""}
                  oninput={(event) =>
                    setNewTaskDate("due_date", event.currentTarget.value)}
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
              <td colspan={8} class="empty-cell">
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
              <tr class="task-data-row">
                <td class="task-title-cell">
                  {#if isEditing(task, "title")}
                    <Input
                      bind:value={cellDraft}
                      aria-label={`Edit ${task.title}`}
                      class="h-9"
                      onblur={() => void saveCell(task, "title")}
                      onkeydown={handleEditorKeydown}
                      autofocus
                    />
                  {:else}
                    <button
                      type="button"
                      class="cell-text task-title"
                      disabled={!canEdit}
                      onclick={() => startEditing(task, "title")}
                    >
                      <span class="block truncate font-medium"
                        >{task.title}</span
                      >
                      {#if task.task_key}
                        <span class="font-mono text-xs text-muted-foreground">
                          {task.task_key}
                        </span>
                      {/if}
                    </button>
                  {/if}
                </td>
                <td>
                  <Select.Root
                    type="single"
                    value={task.task_type_id}
                    onValueChange={(value) =>
                      void updateChoice(task, "task_type_id", value)}
                  >
                    <Select.Trigger
                      class="task-table-select"
                      disabled={!canEdit}
                      aria-label={`Task type for ${task.title}`}
                    >
                      {taskTypes.find((type) => type.id === task.task_type_id)
                        ?.name ?? "Choose type"}
                    </Select.Trigger>
                    <Select.Content>
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
                    value={task.priority}
                    onValueChange={(value) =>
                      void updateChoice(task, "priority", value)}
                  >
                    <Select.Trigger
                      class="task-table-select"
                      disabled={!canEdit}
                      aria-label={`Priority for ${task.title}`}
                    >
                      <Badge
                        variant="outline"
                        style="border-color: {priority.color}; color: {priority.color}"
                      >
                        {priority.label}
                      </Badge>
                    </Select.Trigger>
                    <Select.Content>
                      <Select.Group>
                        {#each priorityOptions as option (option.value)}
                          <Select.Item
                            value={option.value}
                            label={option.label}
                          >
                            {option.label}
                          </Select.Item>
                        {/each}
                      </Select.Group>
                    </Select.Content>
                  </Select.Root>
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
                  {#if isEditing(task, "planned_start_at")}
                    <Input
                      type="date"
                      bind:value={cellDraft}
                      aria-label={`Planned start for ${task.title}`}
                      class="h-9"
                      onblur={() => void saveCell(task, "planned_start_at")}
                      onkeydown={handleEditorKeydown}
                      autofocus
                    />
                  {:else}
                    <button
                      type="button"
                      class="cell-text whitespace-nowrap"
                      disabled={!canEdit}
                      onclick={() => startEditing(task, "planned_start_at")}
                    >
                      {dateLabel(task.planned_start_at)}
                    </button>
                  {/if}
                </td>
                <td>
                  {#if isEditing(task, "planned_end_at")}
                    <Input
                      type="date"
                      bind:value={cellDraft}
                      aria-label={`Planned end for ${task.title}`}
                      class="h-9"
                      onblur={() => void saveCell(task, "planned_end_at")}
                      onkeydown={handleEditorKeydown}
                      autofocus
                    />
                  {:else}
                    <button
                      type="button"
                      class="cell-text whitespace-nowrap"
                      disabled={!canEdit}
                      onclick={() => startEditing(task, "planned_end_at")}
                    >
                      {dateLabel(task.planned_end_at)}
                    </button>
                  {/if}
                </td>
                <td>
                  {#if isEditing(task, "due_date")}
                    <Input
                      type="date"
                      bind:value={cellDraft}
                      aria-label={`Due date for ${task.title}`}
                      class="h-9"
                      onblur={() => void saveCell(task, "due_date")}
                      onkeydown={handleEditorKeydown}
                      autofocus
                    />
                  {:else}
                    <button
                      type="button"
                      class="cell-text whitespace-nowrap"
                      disabled={!canEdit}
                      onclick={() => startEditing(task, "due_date")}
                    >
                      {#if due?.isOverdue}
                        <AlertTriangleIcon class="size-3.5 text-destructive" />
                        <span class="text-destructive">{due.relative}</span>
                      {:else if task.due_date}
                        <span>{due?.relative}</span>
                      {:else}
                        <span class="text-muted-foreground">Set date</span>
                      {/if}
                    </button>
                  {/if}
                </td>
                <td class="details-column">
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    aria-label={`Open details for ${task.title}`}
                    onclick={() => onOpen(task)}
                  >
                    <MoreVerticalIcon />
                  </Button>
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
    border: 1px solid var(--border);
    border-radius: var(--radius-xl);
    background: var(--card);
  }

  .task-table-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    border-bottom: 1px solid var(--border);
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
    background: var(--muted);
    color: var(--muted-foreground);
    font-size: 0.75rem;
    font-weight: 600;
  }

  .task-table td {
    height: 3.75rem;
    border-top: 1px solid var(--border);
    padding: 0.5rem 0.75rem;
    vertical-align: middle;
  }

  .task-data-row:hover {
    background: color-mix(in oklab, var(--muted) 55%, transparent);
  }

  .new-task-row {
    background: color-mix(in oklab, var(--primary) 45%, var(--card));
  }

  .task-title-cell {
    min-width: 13rem;
    max-width: 20rem;
  }

  .details-column {
    width: 1%;
    white-space: nowrap;
  }

  .cell-text {
    display: flex;
    width: 100%;
    min-height: 2rem;
    flex-direction: column;
    justify-content: center;
    gap: 0.15rem;
    border: 1px solid transparent;
    border-radius: var(--radius-sm);
    background: transparent;
    padding: 0.25rem 0.5rem;
    text-align: left;
  }

  .cell-text:hover {
    border-color: var(--border);
    background: var(--background);
  }

  .cell-text:focus-visible {
    outline: 2px solid var(--ring);
    outline-offset: 1px;
  }

  :global(.task-table-select) {
    width: 100%;
    min-height: 2rem;
    height: auto;
    justify-content: flex-start;
    border-color: transparent;
    background: transparent;
    padding: 0.25rem 0.5rem;
    text-align: left;
  }

  :global(.task-table-select:hover) {
    border-color: var(--border);
    background: var(--background);
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
