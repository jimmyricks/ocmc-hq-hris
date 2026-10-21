<script lang="ts">
  import { browser } from "$app/environment";
  import { goto } from "$app/navigation";
  import { listFiltered } from "$lib/api/index.js";
  import { getToken, getUser, isProjectManager } from "$lib/auth";
  import { OFFICIAL_CURRENCY } from "$lib/constants.js";
  import { payrollApi } from "$lib/payroll/api.js";
  import type { PayrollEntry } from "$lib/payroll/types.js";
  import TaskDetailModal from "$lib/components/task-manager/task-detail-modal.svelte";
  import { Badge } from "$lib/components/ui/badge/index.js";
  import { Button } from "$lib/components/ui/button/index.js";
  import * as Card from "$lib/components/ui/card/index.js";
  import * as Stats from "$lib/components/ui/stat/index.js";
  import { Skeleton } from "$lib/components/ui/skeleton/index.js";
  import { taskApi } from "$lib/task-manager/api.js";
  import type {
    Project,
    Task,
    TaskAssignment,
  } from "$lib/task-manager/types.js";
  import {
    formatDueDate,
    PRIORITY_META,
    stateBadge,
    taskState,
  } from "$lib/task-manager/utils.js";

  import ArrowUpRightIcon from "@lucide/svelte/icons/arrow-up-right";
  import BanknoteIcon from "@lucide/svelte/icons/banknote";
  import CalendarDaysIcon from "@lucide/svelte/icons/calendar-days";
  import CheckCircle2Icon from "@lucide/svelte/icons/check-circle-2";
  import CheckSquare2Icon from "@lucide/svelte/icons/check-square-2";
  import ChevronRightIcon from "@lucide/svelte/icons/chevron-right";
  import CircleDashedIcon from "@lucide/svelte/icons/circle-dashed";
  import ClipboardCheckIcon from "@lucide/svelte/icons/clipboard-check";
  import FolderKanbanIcon from "@lucide/svelte/icons/folder-kanban";
  import PlusIcon from "@lucide/svelte/icons/plus";
  import SparklesIcon from "@lucide/svelte/icons/sparkles";

  let projects = $state<Project[]>([]);
  let tasks = $state<Task[]>([]);
  let assignments = $state<TaskAssignment[]>([]);
  let entries = $state<PayrollEntry[]>([]);
  let loading = $state(true);
  let currentUser = $state(getUser());
  let detailOpen = $state(false);
  let detailTaskId = $state<string | null>(null);
  let loadError = $state("");

  let isPM = $derived(isProjectManager(currentUser));
  let assignedTaskIds = $derived(
    new Set(
      assignments.filter((a) => a.is_active !== false).map((a) => a.task_id),
    ),
  );
  let myTasks = $derived(
    tasks.filter((task) => {
      const state = taskState(task);
      return (
        assignedTaskIds.has(task.id) &&
        [
          "draft_assigned",
          "in_progress",
          "needs_revision",
          "for_review",
        ].includes(state)
      );
    }),
  );
  let reviewTasks = $derived(
    tasks.filter((task) => taskState(task) === "for_review"),
  );
  let activeProjects = $derived(
    projects.filter((project) => project.status !== "closed"),
  );
  let upcomingTasks = $derived(
    [...myTasks]
      .filter((task) => task.due_date)
      .sort(
        (a, b) =>
          new Date(a.due_date!).getTime() - new Date(b.due_date!).getTime(),
      )
      .slice(0, 4),
  );
  let paidTotal = $derived(
    entries
      .filter((entry) => entry.status === "paid")
      .reduce((sum, entry) => sum + (Number(entry.total_amount) || 0), 0),
  );
  let dateLabel = $derived(
    new Intl.DateTimeFormat("en-US", {
      weekday: "long",
      month: "long",
      day: "numeric",
    }).format(new Date()),
  );
  let firstName = $derived(
    currentUser?.full_name?.split(" ")[0] || currentUser?.username || "there",
  );

  const statTones: Record<string, string> = {
    success: "bg-success/15 text-success",
    primary: "bg-primary/15 text-primary",
    warning: "bg-warning/15 text-warning",
    secondary: "bg-secondary/15 text-secondary",
  };

  const stats = $derived([
    {
      label: "Active projects",
      value: activeProjects.length,
      note: "Across the workspace",
      icon: FolderKanbanIcon,
      tone: "success",
    },
    {
      label: "My open tasks",
      value: myTasks.length,
      note: "Assigned to you",
      icon: CheckSquare2Icon,
      tone: "primary",
    },
    {
      label: isPM ? "Ready for review" : "In review",
      value: reviewTasks.length,
      note: isPM ? "Waiting on your decision" : "With the project leads",
      icon: ClipboardCheckIcon,
      tone: "warning",
    },
    {
      label: "Paid this period",
      value: formatCurrency(paidTotal),
      note: "Latest payroll run",
      icon: BanknoteIcon,
      tone: "secondary",
    },
  ]);

  function formatCurrency(value: number) {
    return new Intl.NumberFormat("en-PH", {
      style: "currency",
      currency: OFFICIAL_CURRENCY,
      maximumFractionDigits: 0,
    }).format(value);
  }

  function projectName(id: string) {
    return (
      projects.find((project) => project.id === id)?.name ??
      "Unassigned project"
    );
  }

  function projectProgress(projectId: string) {
    const projectTasks = tasks.filter((task) => task.project_id === projectId);
    if (!projectTasks.length) return 0;
    const completed = projectTasks.filter((task) =>
      ["approved", "closed"].includes(taskState(task)),
    ).length;
    return Math.round((completed / projectTasks.length) * 100);
  }

  function openTask(task: Task) {
    detailTaskId = task.id;
    detailOpen = true;
  }

  $effect(() => {
    if (!browser) return;
    if (!getToken()) {
      goto("/login");
      return;
    }
    currentUser = getUser();
    load();
  });

  async function load() {
    loading = true;
    loadError = "";
    try {
      const user = getUser();
      const [projectData, taskData, assignmentData] = await Promise.all([
        taskApi.getProjects(),
        taskApi.getTasksForProject("all"),
        user
          ? listFiltered("task_assignment", [
              { field: "user_id", op: "eq", value: user.id },
            ])
              .then((response) => (response.data ?? []) as TaskAssignment[])
              .catch(() => [] as TaskAssignment[])
          : Promise.resolve([] as TaskAssignment[]),
      ]);
      projects = projectData;
      tasks = taskData;
      assignments = assignmentData;

      try {
        const periods = await payrollApi.getPeriods();
        entries = periods.length
          ? await payrollApi.getEntriesForPeriod(periods[0].id)
          : [];
      } catch {
        entries = [];
      }
    } catch (error) {
      console.error("Failed to load dashboard:", error);
      loadError = "We couldn't load your workspace data. Please try again.";
    } finally {
      loading = false;
    }
  }
</script>

<svelte:head>
  <title>Overview · OCMC HQ</title>
  <meta
    name="description"
    content="Your team workspace: tasks, projects, approvals and payroll at a glance."
  />
</svelte:head>

<div class="dashboard flex flex-col gap-6 sm:gap-8">
  <section
    class="flex flex-col justify-between gap-5 sm:flex-row sm:items-center"
  >
    <div class="space-y-2">
      <p class="eyebrow">{dateLabel}</p>
      <h1 class="text-3xl font-semibold tracking-tight sm:text-4xl">
        Good day, {firstName}<span class="greeting-mark">.</span>
      </h1>
      <p class="max-w-xl text-sm text-base-content/60 sm:text-base">
        Here's what's moving across your team today.
      </p>
    </div>
    <Button
      href="/project/all"
      variant="primary"
      class="self-start sm:self-auto"
    >
      <PlusIcon class="size-4" />
      Create a task
    </Button>
  </section>

  {#if loadError}
    <div
      class="rounded-xl border border-error/20 bg-error/5 px-4 py-3 text-sm text-error"
    >
      {loadError}
    </div>
  {/if}

  <Stats.Root
    class="w-full stats-vertical border border-base-300 bg-base-100 lg:stats-horizontal"
  >
    {#each stats as stat (stat.label)}
      <Stats.Item>
        <Stats.Figure
          class="flex size-10 items-center justify-center rounded-2xl {statTones[
            stat.tone
          ]}"
        >
          <stat.icon class="size-[18px]" />
        </Stats.Figure>
        <Stats.Title>{stat.label}</Stats.Title>
        <Stats.Value class="tabular-nums"
          >{loading ? "—" : stat.value}</Stats.Value
        >
        <Stats.Desc>{stat.note}</Stats.Desc>
      </Stats.Item>
    {/each}
  </Stats.Root>

  <div class="grid gap-5 xl:grid-cols-[minmax(0,1.65fr)_minmax(300px,0.85fr)]">
    <Card.Root class="overflow-hidden">
      <Card.Header
        class="flex-row items-start justify-between gap-3 px-5 py-5 sm:px-6"
      >
        <div>
          <Card.Title>Your work queue</Card.Title>
          <p class="mt-1 text-xs text-base-content/60">
            The next things to move forward.
          </p>
        </div>
        <a
          href="/tasks/my"
          class="inline-flex items-center gap-1 text-xs font-semibold text-primary transition hover:gap-2"
        >
          All tasks <ArrowUpRightIcon class="size-3.5" />
        </a>
      </Card.Header>
      <Card.Content class="p-0">
        {#if loading}
          <div class="space-y-4 p-6">
            {#each Array.from({ length: 4 }) as _, i (i)}
              <Skeleton class="h-12 w-full" />
            {/each}
          </div>
        {:else if myTasks.length === 0}
          <div class="flex flex-col items-center px-6 py-14 text-center">
            <div
              class="mb-4 flex size-12 items-center justify-center rounded-2xl bg-base-200 text-primary"
            >
              <CheckCircle2Icon class="size-6" />
            </div>
            <p class="font-semibold">You're all clear</p>
            <p class="mt-1 max-w-xs text-sm text-base-content/60">
              Tasks assigned to you will show up here when they need attention.
            </p>
          </div>
        {:else}
          <div class="divide-y divide-base-300/70">
            {#each myTasks.slice(0, 6) as task (task.id)}
              {@const badge = stateBadge({
                workflow_state: task.workflow_state,
                status: task.status,
              })}
              {@const due = formatDueDate(task.due_date)}
              <button
                class="task-row flex w-full items-center gap-3 px-5 py-4 text-left transition hover:bg-base-200/60 sm:px-6"
                onclick={() => openTask(task)}
              >
                <span
                  class="priority-mark"
                  style="--priority: {PRIORITY_META[task.priority]?.color ??
                    'var(--color-base-content)'}"
                  aria-label="{task.priority} priority"
                ></span>
                <span class="min-w-0 flex-1">
                  <span class="block truncate text-sm font-semibold"
                    >{task.title}</span
                  >
                  <span
                    class="mt-1 flex items-center gap-2 text-xs text-base-content/60"
                  >
                    <span class="truncate">{projectName(task.project_id)}</span>
                    {#if task.task_key}
                      <span class="font-mono text-[10px]">{task.task_key}</span>
                    {/if}
                  </span>
                </span>
                <span class="hidden shrink-0 text-right sm:block">
                  <span
                    class="block text-xs font-medium {due.isOverdue
                      ? 'text-error'
                      : 'text-base-content/60'}"
                  >
                    {due.relative}
                  </span>
                  <Badge variant={badge.variant} class="mt-1 text-[10px]">
                    {badge.label}
                  </Badge>
                </span>
                <ChevronRightIcon
                  class="size-4 shrink-0 text-base-content/40"
                />
              </button>
            {/each}
          </div>
        {/if}
      </Card.Content>
    </Card.Root>

    <Card.Root class="overflow-hidden">
      <Card.Header class="flex-row items-center justify-between px-5 py-5">
        <div>
          <Card.Title>Coming up</Card.Title>
          <p class="mt-1 text-xs text-base-content/60">
            Your nearest due dates
          </p>
        </div>
        <a
          href="/planner"
          aria-label="Open planner"
          class="flex size-9 items-center justify-center rounded-xl bg-base-200 text-primary transition hover:bg-primary/10"
        >
          <CalendarDaysIcon class="size-4" />
        </a>
      </Card.Header>
      <Card.Content class="flex grow flex-col p-5">
        {#if loading}
          <div class="space-y-4">
            {#each Array.from({ length: 3 }) as _, i (i)}
              <Skeleton class="h-12 w-full" />
            {/each}
          </div>
        {:else if upcomingTasks.length === 0}
          <div class="flex flex-col items-center py-8 text-center">
            <CircleDashedIcon class="mb-3 size-8 text-base-content/40" />
            <p class="text-sm font-semibold">Nothing on the calendar</p>
            <p class="mt-1 text-xs text-base-content/60">
              Tasks with due dates will appear here.
            </p>
          </div>
        {:else}
          <div class="relative flex flex-col">
            <div class="timeline-rail" aria-hidden="true"></div>
            {#each upcomingTasks as task (task.id)}
              {@const due = formatDueDate(task.due_date)}
              <button
                class="timeline-item relative flex gap-3 pb-5 text-left last:pb-0"
                onclick={() => openTask(task)}
              >
                <span class="timeline-dot" class:overdue={due.isOverdue}></span>
                <span class="min-w-0 flex-1">
                  <span class="flex items-center justify-between gap-2">
                    <span class="truncate text-sm font-semibold"
                      >{task.title}</span
                    >
                    <span
                      class="shrink-0 text-[11px] font-medium {due.isOverdue
                        ? 'text-error'
                        : 'text-base-content/60'}"
                    >
                      {due.relative}
                    </span>
                  </span>
                  <span
                    class="mt-1 block truncate text-xs text-base-content/60"
                  >
                    {projectName(task.project_id)}
                  </span>
                </span>
              </button>
            {/each}
          </div>
        {/if}
        <Card.Action class="mt-auto justify-end">
          <a href="/planner" class="btn btn-primary">
            Open team planner
            <ArrowUpRightIcon class="size-4" />
          </a>
        </Card.Action>
      </Card.Content>
    </Card.Root>
  </div>

  <section
    class="grid gap-5 xl:grid-cols-[minmax(0,1.65fr)_minmax(300px,0.85fr)]"
  >
    <Card.Root>
      <Card.Header
        class="flex-row items-center justify-between gap-3 px-5 py-5 sm:px-6"
      >
        <div>
          <Card.Title>Projects in motion</Card.Title>
          <p class="mt-1 text-xs text-base-content/60">
            A pulse on active team work
          </p>
        </div>
        <a
          href="/project/all"
          class="inline-flex items-center gap-1 text-xs font-semibold text-primary"
        >
          Browse projects <ArrowUpRightIcon class="size-3.5" />
        </a>
      </Card.Header>
      <Card.Content class="grid gap-3 px-5 pb-5 sm:grid-cols-2 sm:px-6">
        {#if loading}
          {#each Array.from({ length: 2 }) as _, i (i)}
            <Skeleton class="h-24 w-full rounded-2xl" />
          {/each}
        {:else if activeProjects.length === 0}
          <div
            class="col-span-full rounded-2xl border border-dashed border-base-300 px-5 py-8 text-center text-sm text-base-content/60"
          >
            No active projects yet.
          </div>
        {:else}
          {#each activeProjects.slice(0, 4) as project (project.id)}
            {@const progress = projectProgress(project.id)}
            <a
              href="/project/{project.id}"
              class="project-tile rounded-2xl border border-base-300/70 p-4 transition hover:-translate-y-0.5 hover:border-primary/30 hover:shadow-sm"
            >
              <div class="flex items-start justify-between gap-3">
                <div class="flex min-w-0 items-center gap-3">
                  <span
                    class="size-2.5 shrink-0 rounded-full"
                    style="background-color: {project.color ||
                      'var(--color-base-content)'}"
                  ></span>
                  <span class="truncate text-sm font-semibold"
                    >{project.name}</span
                  >
                </div>
                <ArrowUpRightIcon
                  class="size-4 shrink-0 text-base-content/60"
                />
              </div>
              <div
                class="mt-5 flex items-center justify-between text-[11px] text-base-content/60"
              >
                <span
                  >{tasks.filter((task) => task.project_id === project.id)
                    .length} tasks</span
                >
                <span class="font-semibold text-base-content">{progress}%</span>
              </div>
              <div class="mt-2 h-1.5 overflow-hidden rounded-full bg-base-200">
                <div
                  class="h-full rounded-full bg-primary transition-[width]"
                  style="width: {progress}%"
                ></div>
              </div>
            </a>
          {/each}
        {/if}
      </Card.Content>
    </Card.Root>

    <Card.Root class="overflow-hidden">
      <Card.Content
        class="relative flex h-full min-h-56 flex-col justify-between p-6 sm:p-7"
      >
        <div class="relative">
          <div
            class="pulse-mark mb-5 flex size-10 items-center justify-center rounded-lg"
          >
            <SparklesIcon class="size-5" />
          </div>
          <p
            class="text-xs font-semibold uppercase tracking-[0.15em] text-base-content/60"
          >
            Team pulse
          </p>
          <h2
            class="mt-2 max-w-xs text-2xl font-semibold tracking-tight text-base-content"
          >
            {#if isPM && reviewTasks.length > 0}
              {reviewTasks.length}
              {reviewTasks.length === 1 ? "task needs" : "tasks need"} your review.
            {:else}
              Make space for focused work.
            {/if}
          </h2>
          <p class="mt-2 max-w-xs text-sm leading-relaxed text-base-content/60">
            {#if isPM && reviewTasks.length > 0}
              A quick review keeps work flowing and payments on schedule.
            {:else}
              Keep tasks moving and your team's shared plan stays clear.
            {/if}
          </p>
        </div>
        <a
          href={isPM && reviewTasks.length ? "/project/all" : "/tasks/my"}
          class="pulse-link relative mt-7 inline-flex w-fit items-center gap-2 rounded-lg px-4 py-2.5 text-xs font-bold transition"
        >
          {isPM && reviewTasks.length ? "Review submissions" : "View my tasks"}
          <ArrowUpRightIcon class="size-3.5" />
        </a>
      </Card.Content>
    </Card.Root>
  </section>
</div>

<TaskDetailModal bind:open={detailOpen} taskId={detailTaskId} {projects} />

<style>
  .dashboard {
    animation: arrive 420ms cubic-bezier(0.2, 0.75, 0.25, 1) both;
  }

  .eyebrow {
    color: color-mix(in oklab, var(--color-base-content) 62%, transparent);
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.14em;
    text-transform: uppercase;
  }

  .greeting-mark {
    color: var(--color-primary);
  }

  .priority-mark {
    width: 3px;
    height: 2.2rem;
    flex: 0 0 3px;
    border-radius: 99px;
    background: var(--priority);
  }

  .timeline-rail {
    position: absolute;
    top: 0.45rem;
    bottom: 0.45rem;
    left: 0.27rem;
    width: 1px;
    background: var(--color-base-300);
  }

  .timeline-dot {
    z-index: 1;
    margin-top: 0.28rem;
    width: 0.62rem;
    height: 0.62rem;
    flex: 0 0 0.62rem;
    border: 2px solid var(--color-base-100);
    border-radius: 50%;
    background: var(--color-primary);
  }

  .timeline-dot.overdue {
    background: var(--color-error);
  }

  .pulse-mark {
    background: color-mix(
      in oklab,
      var(--color-primary) 12%,
      var(--color-base-100)
    );
    color: var(--color-primary);
  }

  .pulse-link {
    background: var(--color-primary);
    color: var(--color-primary-content);
  }

  .pulse-link:hover {
    background: color-mix(
      in oklab,
      var(--color-primary) 88%,
      var(--color-base-100)
    );
  }

  @keyframes arrive {
    from {
      opacity: 0;
      transform: translateY(8px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .dashboard {
      animation: none;
    }
    .task-row,
    .project-tile {
      transition: none;
    }
  }
</style>
