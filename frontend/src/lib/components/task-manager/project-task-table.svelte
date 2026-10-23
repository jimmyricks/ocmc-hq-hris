<script lang="ts">
  import * as Empty from "$lib/components/ui/empty/index.js";
  import { Badge } from "$lib/components/ui/badge/index.js";
  import { Button } from "$lib/components/ui/button/index.js";
  import { Skeleton } from "$lib/components/ui/skeleton/index.js";
  import Pagination from "$lib/components/pagination.svelte";
  import type { Task, TaskSummary, TaskType } from "$lib/task-manager/types.js";
  import {
    formatDueDate,
    PRIORITY_META,
    stateBadge,
  } from "$lib/task-manager/utils.js";

  import AlertTriangleIcon from "@lucide/svelte/icons/alert-triangle";
  import ArrowUpRightIcon from "@lucide/svelte/icons/arrow-up-right";
  import ExternalLinkIcon from "@lucide/svelte/icons/external-link";
  import FileTextIcon from "@lucide/svelte/icons/file-text";
  import PlusIcon from "@lucide/svelte/icons/plus";

  type Props = {
    tasks: Task[];
    loading: boolean;
    taskTypes: TaskType[];
    summaries?: Record<string, TaskSummary>;
    canCreate: boolean;
    onAddTask?: () => void;
    onOpen: (task: Task) => void;
    page?: number;
    pageSize?: number;
    total?: number;
    onPageChange?: (page: number) => void;
    onPageSizeChange?: (pageSize: number) => void;
  };

  let {
    tasks,
    loading,
    taskTypes,
    summaries = {},
    canCreate,
    onAddTask,
    onOpen,
    page = 1,
    pageSize = 25,
    total = 0,
    onPageChange,
    onPageSizeChange,
  }: Props = $props();

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
    <Button onclick={onAddTask} disabled={loading || !canCreate}>
      <PlusIcon data-icon="inline-start" />
      New Task
    </Button>
  </div>

  <div class="task-table-scroll">
    <table class="table table-zebra task-table">
      <colgroup>
        <col />
        <col class="task-col-type" />
        <col class="task-col-assignee" />
        <col class="task-col-priority" />
        <col class="task-col-state" />
        <col class="task-col-due" />
        <col class="task-col-icon" />
        <col class="task-col-icon" />
      </colgroup>
      <thead>
        <tr>
          <th>Task</th>
          <th>Type</th>
          <th>Assignee</th>
          <th>Priority</th>
          <th>State</th>
          <th>Due</th>
          <th>Link</th>
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
        {:else if tasks.length === 0}
          <tr>
            <td colspan={8} class="empty-cell">
              <Empty.Root>
                <Empty.Media variant="icon">
                  <PlusIcon />
                </Empty.Media>
                <Empty.Header>
                  <Empty.Title>No tasks yet</Empty.Title>
                  <Empty.Description>
                    Add a task to get started.
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
            {@const summary = summaries[task.id]}
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
                <span class="block truncate">
                  {taskTypes.find((type) => type.id === task.task_type_id)
                    ?.name ?? "—"}
                </span>
              </td>
              <td>
                {#if summary?.assignee_name}
                  <span class="block truncate">
                    {summary.assignee_name}
                  </span>
                {:else}
                  <span class="text-base-content/60">Unassigned</span>
                {/if}
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
              <td>
                {#if summary?.deliverable_url}
                  <a
                    href={summary.deliverable_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    class="inline-flex items-center text-primary"
                    aria-label="Open submitted link for {task.title}"
                    title={summary.deliverable_url}
                    onclick={(event) => event.stopPropagation()}
                  >
                    <ExternalLinkIcon class="size-4" />
                  </a>
                {:else if summary?.has_deliverable}
                  <span
                    class="inline-flex items-center text-base-content/70"
                    title="Text deliverable submitted"
                  >
                    <FileTextIcon class="size-4" />
                  </span>
                {:else}
                  <span class="text-base-content/40">—</span>
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
      </tbody>
    </table>
  </div>
  {#if onPageChange}
    <Pagination
      {page}
      {pageSize}
      {total}
      {loading}
      pageSizeOptions={[10, 25, 50, 100]}
      onchange={onPageChange}
      onpagesizechange={onPageSizeChange}
    />
  {/if}
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
    table-layout: fixed;
    border-collapse: collapse;
    text-align: left;
    font-size: 0.875rem;
  }

  .task-table th {
    height: 2.5rem;
    padding: 0 0.75rem;
    background: var(--color-base-200);
    color: color-mix(in oklab, var(--color-base-content) 62%, transparent);
    font-size: 0.75rem;
    font-weight: 600;
    white-space: nowrap;
  }

  .task-table td {
    height: 3.75rem;
    border-top: 1px solid var(--color-base-300);
    padding: 0.5rem 0.75rem;
    vertical-align: middle;
    overflow: hidden;
  }

  .task-col-type {
    width: 9rem;
  }
  .task-col-assignee {
    width: 10rem;
  }
  .task-col-priority {
    width: 6rem;
  }
  .task-col-state {
    width: 8.5rem;
  }
  .task-col-due {
    width: 7rem;
  }
  .task-col-icon {
    width: 3.25rem;
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

  .details-column {
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
  }
</style>
