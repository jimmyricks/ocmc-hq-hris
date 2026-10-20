<script lang="ts">
  import { browser } from "$app/environment";
  import { goto } from "$app/navigation";
  import { getToken } from "$lib/auth";
  import TaskDetailModal from "$lib/components/task-manager/task-detail-modal.svelte";
  import * as Dialog from "$lib/components/ui/dialog/index.js";
  import * as Field from "$lib/components/ui/field/index.js";
  import * as Select from "$lib/components/ui/select/index.js";
  import { Button } from "$lib/components/ui/button/index.js";
  import { Input } from "$lib/components/ui/input/index.js";
  import { Badge } from "$lib/components/ui/badge/index.js";
  import * as Card from "$lib/components/ui/card/index.js";
  import { Skeleton } from "$lib/components/ui/skeleton/index.js";
  import { workspaceApi } from "$lib/workspaces/api";
  import type {
    PlannerActivity,
    WorkspaceContext,
  } from "$lib/workspaces/types";
  import { taskApi } from "$lib/task-manager/api.js";
  import type { Project } from "$lib/task-manager/types.js";

  import ArrowLeftIcon from "@lucide/svelte/icons/arrow-left";
  import ArrowRightIcon from "@lucide/svelte/icons/arrow-right";
  import CalendarDaysIcon from "@lucide/svelte/icons/calendar-days";
  import ChevronDownIcon from "@lucide/svelte/icons/chevron-down";
  import PlusIcon from "@lucide/svelte/icons/plus";

  type CalendarCell = {
    date: Date;
    key: string;
    inMonth: boolean;
    activities: PlannerActivity[];
  };

  let projects = $state<Project[]>([]);
  let activities = $state<PlannerActivity[]>([]);
  let loading = $state(true);
  let errorMessage = $state("");
  let month = $state(
    new Date(new Date().getFullYear(), new Date().getMonth(), 1),
  );
  let selectedDate = $state(dateKey(new Date()));
  let selectedProject = $state("all");
  let view = $state<"month" | "agenda">("month");
  let detailOpen = $state(false);
  let detailTaskId = $state<string | null>(null);
  let workspaceContext = $state<WorkspaceContext | null>(null);
  let activityOpen = $state(false);
  let activitySaving = $state(false);
  let activityTitle = $state("");
  let activityDescription = $state("");
  let activityType = $state("plan");
  let activityProjectId = $state("");
  let activityWorkspaceId = $state("");
  let activityTeamId = $state("");
  let activityResourceId = $state("");
  let activityStartsAt = $state("");
  let activityEndsAt = $state("");
  let recurrence = $state("none");
  let recurrenceUntil = $state("");
  let recurrenceInterval = $state("1");
  let resources = $state<
    Array<{
      id: string;
      workspace_id: string;
      name: string;
      resource_type: string;
    }>
  >([]);
  let teams = $state<Array<{ id: string; name: string }>>([]);
  const canManage = $derived(Boolean(workspaceContext?.can_manage));
  const composerWorkspaceId = $derived(
    projects.find((project) => project.id === activityProjectId)
      ?.workspace_id ??
      activityWorkspaceId ??
      workspaceContext?.active_workspace_id ??
      "",
  );
  const filteredResources = $derived(
    resources.filter(
      (resource) => resource.workspace_id === composerWorkspaceId,
    ),
  );
  const selectedComposerWorkspace = $derived(
    workspaceContext?.workspaces.find(
      (workspace) => workspace.id === composerWorkspaceId,
    ),
  );

  const weekdayNames = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
  const monthHeading = $derived(
    new Intl.DateTimeFormat("en-US", { month: "long", year: "numeric" }).format(
      month,
    ),
  );
  const filteredActivities = $derived(
    activities.filter(
      (activity) =>
        selectedProject === "all" || activity.project?.id === selectedProject,
    ),
  );
  const monthCells = $derived.by(() => {
    const first = new Date(month.getFullYear(), month.getMonth(), 1);
    const offset = (first.getDay() + 6) % 7;
    const start = new Date(first);
    start.setDate(first.getDate() - offset);

    return Array.from({ length: 42 }, (_, index): CalendarCell => {
      const date = new Date(start);
      date.setDate(start.getDate() + index);
      const key = dateKey(date);
      return {
        date,
        key,
        inMonth: date.getMonth() === month.getMonth(),
        activities: filteredActivities.filter((activity) =>
          activityCoversDate(activity, key),
        ),
      };
    });
  });
  const monthActivities = $derived(
    filteredActivities
      .filter((activity) =>
        activityCoversRange(
          activity,
          dateKey(new Date(month.getFullYear(), month.getMonth(), 1)),
          dateKey(new Date(month.getFullYear(), month.getMonth() + 1, 0)),
        ),
      )
      .sort((a, b) => (a.starts_at ?? "").localeCompare(b.starts_at ?? "")),
  );
  const selectedActivities = $derived(
    filteredActivities.filter((activity) =>
      activityCoversDate(activity, selectedDate),
    ),
  );
  const nextUp = $derived.by(() => {
    const start = dateKey(new Date());
    const endDate = new Date();
    endDate.setDate(endDate.getDate() + 14);
    const end = dateKey(endDate);
    return filteredActivities
      .filter((activity) => {
        const date = activity.starts_at?.slice(0, 10);
        return date && date >= start && date <= end;
      })
      .sort((a, b) => (a.starts_at ?? "").localeCompare(b.starts_at ?? ""))
      .slice(0, 5);
  });

  function dateKey(date: Date) {
    const year = date.getFullYear();
    const monthValue = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${year}-${monthValue}-${day}`;
  }

  function changeMonth(amount: number) {
    month = new Date(month.getFullYear(), month.getMonth() + amount, 1);
    selectedDate = dateKey(month);
    load();
  }

  function goToToday() {
    const today = new Date();
    month = new Date(today.getFullYear(), today.getMonth(), 1);
    selectedDate = dateKey(today);
    load();
  }

  function openActivity(activity: PlannerActivity) {
    if (activity.source_type === "task") {
      detailTaskId = activity.source_id;
      detailOpen = true;
    } else if (activity.starts_at) {
      selectedDate = activity.starts_at.slice(0, 10);
    }
  }

  function localDateTimeValue(date: Date) {
    const local = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
    return local.toISOString().slice(0, 16);
  }

  async function openActivityComposer() {
    const context = workspaceContext ?? (await workspaceApi.getContext());
    workspaceContext = context;
    activityTitle = "";
    activityDescription = "";
    activityType = "plan";
    activityProjectId = "";
    activityWorkspaceId =
      context.active_workspace_id ??
      (context.is_global ? "" : (context.workspaces[0]?.id ?? ""));
    activityTeamId = "";
    activityResourceId = "";
    const starts = new Date();
    starts.setMinutes(0, 0, 0);
    starts.setHours(starts.getHours() + 1);
    const ends = new Date(starts);
    ends.setHours(ends.getHours() + 1);
    activityStartsAt = localDateTimeValue(starts);
    activityEndsAt = localDateTimeValue(ends);
    recurrence = "none";
    const until = new Date(starts);
    until.setDate(until.getDate() + 28);
    recurrenceUntil = dateKey(until);
    recurrenceInterval = "1";
    resources = await workspaceApi.getResources();
    activityOpen = true;
  }

  async function createActivity() {
    if (!activityTitle.trim() || !activityStartsAt || !activityEndsAt) return;
    const workspaceId = composerWorkspaceId;
    if (!workspaceId) {
      errorMessage = "Select a company workspace before creating an activity.";
      return;
    }
    if (new Date(activityEndsAt) <= new Date(activityStartsAt)) {
      errorMessage = "The activity end must be later than its start.";
      return;
    }

    activitySaving = true;
    errorMessage = "";
    try {
      const common = {
        title: activityTitle.trim(),
        description: activityDescription.trim() || undefined,
        project_id: activityProjectId || undefined,
        team_id: activityTeamId || undefined,
        workspace_id: workspaceId,
        starts_at: new Date(activityStartsAt).toISOString(),
        ends_at: new Date(activityEndsAt).toISOString(),
        timezone: selectedComposerWorkspace?.timezone ?? "UTC",
        resource_id: activityResourceId || undefined,
      };
      if (recurrence === "none") {
        await workspaceApi.createEvent({
          ...common,
          event_type: activityType,
          all_day: false,
        });
      } else {
        const startWeekday = (new Date(activityStartsAt).getDay() + 6) % 7;
        await workspaceApi.createSeries({
          ...common,
          event_type: ["lesson", "recording", "event"].includes(activityType)
            ? activityType
            : "event",
          frequency: recurrence,
          interval: Number(recurrenceInterval) || 1,
          weekdays: recurrence === "weekly" ? [startWeekday] : [],
          until_date: recurrenceUntil,
        });
      }
      activityOpen = false;
      await load();
    } catch (error: any) {
      errorMessage = error.message || "The activity could not be saved.";
    } finally {
      activitySaving = false;
    }
  }

  function activityCoversDate(activity: PlannerActivity, key: string) {
    const start = activity.starts_at?.slice(0, 10);
    const end = activity.ends_at?.slice(0, 10);
    if (!start || !end) return false;
    const endIsMidnight = activity.ends_at?.slice(11, 19) === "00:00:00";
    const lastDateObject = new Date(`${end}T00:00:00`);
    if (endIsMidnight && end > start) {
      lastDateObject.setDate(lastDateObject.getDate() - 1);
    }
    const lastDate = dateKey(lastDateObject);
    return key >= start && key <= lastDate;
  }

  function activityCoversRange(
    activity: PlannerActivity,
    start: string,
    end: string,
  ) {
    return (
      activityCoversDate(activity, end) ||
      activityCoversDate(activity, start) ||
      Boolean(
        activity.starts_at &&
          activity.starts_at.slice(0, 10) > start &&
          activity.starts_at.slice(0, 10) < end,
      )
    );
  }

  function activitySubtitle(activity: PlannerActivity) {
    return (
      [
        activity.project?.name,
        activity.team?.name,
        ...activity.resources.map((resource) => resource.name),
      ]
        .filter(Boolean)
        .join(" · ") || activity.workspace.name
    );
  }

  function dueDateLabel(iso?: string | null) {
    if (!iso) return "No due date";
    return new Intl.DateTimeFormat("en-US", {
      weekday: "short",
      month: "short",
      day: "numeric",
    }).format(new Date(`${iso.slice(0, 10)}T00:00:00`));
  }

  $effect(() => {
    if (!browser) return;
    if (!getToken()) {
      goto("/login");
      return;
    }
    load();
  });

  $effect(() => {
    if (!activityOpen || !composerWorkspaceId) {
      teams = [];
      return;
    }
    workspaceApi
      .getTeams(composerWorkspaceId)
      .then((rows) => (teams = rows))
      .catch(() => (teams = []));
  });

  async function load() {
    loading = true;
    errorMessage = "";
    try {
      const first = new Date(month.getFullYear(), month.getMonth(), 1);
      const offset = (first.getDay() + 6) % 7;
      const rangeStart = new Date(first);
      rangeStart.setDate(first.getDate() - offset);
      const rangeEnd = new Date(rangeStart);
      rangeEnd.setDate(rangeStart.getDate() + 42);
      const [projectData, activityData, contextData] = await Promise.all([
        taskApi.getProjects(),
        workspaceApi.getPlannerActivities(
          rangeStart.toISOString(),
          rangeEnd.toISOString(),
        ),
        workspaceApi.getContext(),
      ]);
      projects = projectData;
      activities = activityData;
      workspaceContext = contextData;
    } catch (error) {
      console.error("Failed to load planner:", error);
      errorMessage = "The planner couldn't load. Refresh to try again.";
    } finally {
      loading = false;
    }
  }
</script>

<svelte:head>
  <title>Planner · OCMC HQ</title>
  <meta
    name="description"
    content="See upcoming team work and project deadlines in one calendar."
  />
</svelte:head>

<div class="planner flex flex-col gap-6">
  <section class="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
    <div class="space-y-2">
      <p class="eyebrow">Workspace calendar</p>
      <h1 class="text-3xl font-semibold tracking-tight sm:text-4xl">
        Team planner
      </h1>
      <p class="max-w-xl text-sm text-muted-foreground sm:text-base">
        Authorized tasks, plans, lessons, and studio bookings in one calendar.
      </p>
    </div>
    <div class="flex flex-wrap gap-2 self-start sm:self-auto">
      {#if canManage}
        <Button variant="outline" onclick={openActivityComposer}>
          <CalendarDaysIcon data-icon="inline-start" />
          Add activity
        </Button>
      {/if}
      <a
        href="/project/all"
        class="inline-flex h-10 items-center justify-center gap-2 self-start rounded-lg bg-primary px-5 text-sm font-semibold text-primary-foreground shadow-sm transition hover:-translate-y-0.5 hover:shadow-md sm:self-auto"
      >
        <PlusIcon class="size-4" />
        Add task
      </a>
    </div>
  </section>

  {#if errorMessage}
    <div
      class="rounded-xl border border-destructive/20 bg-destructive/5 px-4 py-3 text-sm text-destructive"
    >
      {errorMessage}
    </div>
  {/if}

  <div class="grid items-start gap-5 2xl:grid-cols-[minmax(0,1fr)_310px]">
    <Card.Root class="overflow-hidden border-border/80 shadow-sm">
      <div
        class="flex flex-col gap-4 border-b border-border/70 p-4 sm:flex-row sm:items-center sm:justify-between sm:px-5"
      >
        <div class="flex items-center gap-3">
          <div class="flex items-center gap-1 rounded-xl bg-secondary p-1">
            <button
              class="flex size-8 items-center justify-center rounded-md text-muted-foreground transition hover:bg-card hover:text-foreground"
              aria-label="Previous month"
              onclick={() => changeMonth(-1)}
            >
              <ArrowLeftIcon class="size-4" />
            </button>
            <button
              class="flex size-8 items-center justify-center rounded-md text-muted-foreground transition hover:bg-card hover:text-foreground"
              aria-label="Next month"
              onclick={() => changeMonth(1)}
            >
              <ArrowRightIcon class="size-4" />
            </button>
          </div>
          <div>
            <h2 class="text-lg font-semibold tracking-tight">{monthHeading}</h2>
            <p class="text-[11px] text-muted-foreground">
              {loading
                ? "Loading activity…"
                : `${monthActivities.length} scheduled ${monthActivities.length === 1 ? "activity" : "activities"}`}
            </p>
          </div>
          <button
            class="ml-1 rounded-md border border-border/80 bg-card px-3 py-1.5 text-xs font-semibold transition hover:border-primary/40 hover:text-primary"
            onclick={goToToday}
          >
            Today
          </button>
        </div>

        <div class="flex flex-wrap items-center gap-2">
          <label class="relative">
            <span class="sr-only">Filter by project</span>
            <select
              bind:value={selectedProject}
              class="h-9 max-w-[200px] appearance-none rounded-md border border-border/80 bg-card py-0 pl-3 pr-8 text-xs font-medium outline-none transition focus:border-primary"
            >
              <option value="all">All projects</option>
              {#each projects as project (project.id)}
                <option value={project.id}>{project.name}</option>
              {/each}
            </select>
            <ChevronDownIcon
              class="pointer-events-none absolute right-3 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground"
            />
          </label>
          <div class="flex rounded-md bg-secondary p-1">
            <button
              class="rounded-sm px-3 py-1.5 text-xs font-semibold transition"
              class:active-view={view === "month"}
              aria-pressed={view === "month"}
              onclick={() => (view = "month")}
            >
              Month
            </button>
            <button
              class="rounded-sm px-3 py-1.5 text-xs font-semibold transition"
              class:active-view={view === "agenda"}
              aria-pressed={view === "agenda"}
              onclick={() => (view = "agenda")}
            >
              Agenda
            </button>
          </div>
        </div>
      </div>

      {#if view === "month"}
        <div class="calendar-wrap">
          <div class="calendar-grid weekday-row">
            {#each weekdayNames as day (day)}
              <div class="weekday-label">{day}</div>
            {/each}
          </div>
          {#if loading}
            <div class="calendar-grid loading-grid">
              {#each Array.from({ length: 42 }) as _, index (index)}
                <div class="calendar-cell"><Skeleton class="h-4 w-5" /></div>
              {/each}
            </div>
          {:else}
            <div class="calendar-grid">
              {#each monthCells as cell (cell.key)}
                <button
                  class="calendar-cell group text-left transition"
                  class:outside={!cell.inMonth}
                  class:selected={selectedDate === cell.key}
                  class:today={cell.key === dateKey(new Date())}
                  aria-label="{cell.date.toLocaleDateString('en-US', {
                    month: 'long',
                    day: 'numeric',
                  })}, {cell.activities.length} activities"
                  aria-pressed={selectedDate === cell.key}
                  onclick={() => (selectedDate = cell.key)}
                >
                  <span class="day-number">{cell.date.getDate()}</span>
                  {#if cell.activities.length > 0}
                    <span class="task-indicators">
                      {#each cell.activities.slice(0, 3) as activity (activity.id)}
                        <span
                          class="task-pill"
                          style="--task-color: {activity.workspace.color}"
                        >
                          <span class="task-pill-dot"></span>
                          <span class="hidden truncate sm:inline"
                            >{activity.title}</span
                          >
                        </span>
                      {/each}
                    </span>
                  {/if}
                  {#if cell.activities.length > 3}
                    <span class="more-count"
                      >+{cell.activities.length - 3} more</span
                    >
                  {/if}
                </button>
              {/each}
            </div>
          {/if}
        </div>
      {:else}
        <div class="agenda-list divide-y divide-border/70">
          {#if loading}
            <div class="space-y-4 p-6">
              {#each Array.from({ length: 5 }) as _, i (i)}
                <Skeleton class="h-14 w-full" />
              {/each}
            </div>
          {:else if monthActivities.length === 0}
            <div class="px-6 py-16 text-center">
              <CalendarDaysIcon
                class="mx-auto size-8 text-muted-foreground/50"
              />
              <p class="mt-3 font-semibold">A clear month ahead</p>
              <p class="mt-1 text-sm text-muted-foreground">
                Scheduled tasks, plans, and sessions will appear here.
              </p>
            </div>
          {:else}
            {#each monthActivities as activity (activity.id)}
              <button
                class="flex w-full items-center gap-4 px-5 py-4 text-left transition hover:bg-muted/50"
                onclick={() => openActivity(activity)}
              >
                <span
                  class="agenda-date shrink-0 rounded-xl px-3 py-2 text-center"
                  style="--task-color: {activity.workspace.color}"
                >
                  <span
                    class="block text-[10px] font-bold uppercase tracking-wider"
                    >{new Date(
                      `${activity.starts_at!.slice(0, 10)}T00:00:00`,
                    ).toLocaleDateString("en-US", { month: "short" })}</span
                  >
                  <span class="block text-lg font-semibold leading-none"
                    >{new Date(
                      `${activity.starts_at!.slice(0, 10)}T00:00:00`,
                    ).getDate()}</span
                  >
                </span>
                <span class="min-w-0 flex-1">
                  <span class="block truncate text-sm font-semibold"
                    >{activity.title}</span
                  >
                  <span
                    class="mt-1 block truncate text-xs text-muted-foreground"
                    >{activitySubtitle(activity)}</span
                  >
                </span>
                <span class="hidden items-center gap-2 sm:flex">
                  <Badge variant="secondary">{activity.workspace.name}</Badge>
                </span>
              </button>
            {/each}
          {/if}
        </div>
      {/if}
    </Card.Root>

    <div class="flex flex-col gap-5">
      <Card.Root class="border-border/80 shadow-sm">
        <Card.Header class="px-5 pb-3 pt-5">
          <div class="flex items-center justify-between">
            <div>
              <Card.Title class="text-base">Selected day</Card.Title>
              <Card.Description class="mt-1">
                {new Date(`${selectedDate}T00:00:00`).toLocaleDateString(
                  "en-US",
                  {
                    weekday: "long",
                    month: "long",
                    day: "numeric",
                  },
                )}
              </Card.Description>
            </div>
            <CalendarDaysIcon class="size-5 text-primary" />
          </div>
        </Card.Header>
        <Card.Content class="px-5 pb-5">
          {#if loading}
            <div class="space-y-3">
              <Skeleton class="h-12 w-full" />
              <Skeleton class="h-12 w-full" />
            </div>
          {:else if selectedActivities.length === 0}
            <p
              class="rounded-xl bg-muted/60 px-4 py-5 text-center text-xs leading-relaxed text-muted-foreground"
            >
              No activity is scheduled for this day. Pick a date with a marker
              to see what's planned.
            </p>
          {:else}
            <div class="flex flex-col gap-2">
              {#each selectedActivities as activity (activity.id)}
                <button
                  class="rounded-xl border border-border/70 p-3 text-left transition hover:border-primary/40 hover:bg-muted/40"
                  onclick={() => openActivity(activity)}
                >
                  <span class="block text-sm font-semibold"
                    >{activity.title}</span
                  >
                  <span class="mt-1.5 flex items-center justify-between gap-2">
                    <span class="truncate text-[11px] text-muted-foreground"
                      >{activitySubtitle(activity)}</span
                    >
                    <span
                      class="size-2 shrink-0 rounded-full"
                      style="background: {activity.workspace.color}"
                    ></span>
                  </span>
                </button>
              {/each}
            </div>
          {/if}
        </Card.Content>
      </Card.Root>

      <Card.Root class="border-border/80 shadow-sm">
        <Card.Header class="px-5 pb-3 pt-5">
          <div class="flex items-center justify-between">
            <div>
              <Card.Title class="text-base">Coming up</Card.Title>
              <Card.Description class="mt-1">Next two weeks</Card.Description>
            </div>
            <span
              class="rounded-md bg-secondary px-2.5 py-1 text-[10px] font-bold text-secondary-foreground"
              >{nextUp.length}</span
            >
          </div>
        </Card.Header>
        <Card.Content class="px-5 pb-5">
          {#if loading}
            <div class="space-y-3">
              {#each Array.from({ length: 3 }) as _, i (i)}
                <Skeleton class="h-10 w-full" />
              {/each}
            </div>
          {:else if nextUp.length === 0}
            <p class="text-xs leading-relaxed text-muted-foreground">
              No scheduled activity in the next two weeks.
            </p>
          {:else}
            <div class="flex flex-col gap-3">
              {#each nextUp as activity (activity.id)}
                <button
                  class="flex items-start gap-3 text-left"
                  onclick={() => openActivity(activity)}
                >
                  <span
                    class="mt-1 size-2 shrink-0 rounded-full"
                    style="background: {activity.workspace.color}"
                  ></span>
                  <span class="min-w-0 flex-1">
                    <span class="block truncate text-xs font-semibold"
                      >{activity.title}</span
                    >
                    <span
                      class="mt-1 block truncate text-[10px] text-muted-foreground"
                      >{activitySubtitle(activity)}</span
                    >
                  </span>
                  <span
                    class="shrink-0 text-[10px] font-medium text-muted-foreground"
                    >{dueDateLabel(activity.starts_at)}</span
                  >
                </button>
              {/each}
            </div>
          {/if}
        </Card.Content>
      </Card.Root>
    </div>
  </div>
</div>

<TaskDetailModal bind:open={detailOpen} taskId={detailTaskId} {projects} />

<Dialog.Root bind:open={activityOpen}>
  <Dialog.Content class="max-w-xl">
    <Dialog.Header>
      <Dialog.Title>Add planned activity</Dialog.Title>
      <Dialog.Description>
        Schedule a company event, milestone, lesson, recording session, or
        recurring series.
      </Dialog.Description>
    </Dialog.Header>

    <Field.FieldGroup class="py-2">
      <Field.Field>
        <Field.Label for="planner-title">Title</Field.Label>
        <Input id="planner-title" bind:value={activityTitle} maxlength={255} />
      </Field.Field>

      <div class="grid gap-4 sm:grid-cols-2">
        <Field.Field>
          <Field.Label for="planner-type">Activity type</Field.Label>
          <Select.Root
            type="single"
            value={activityType}
            onValueChange={(value) => (activityType = value ?? "plan")}
          >
            <Select.Trigger id="planner-type" class="w-full">
              <span class="capitalize">{activityType}</span>
            </Select.Trigger>
            <Select.Content>
              <Select.Group>
                {#each ["plan", "milestone", "event", "lesson", "recording"] as kind (kind)}
                  <Select.Item value={kind} label={kind}>
                    <span class="capitalize">{kind}</span>
                  </Select.Item>
                {/each}
              </Select.Group>
            </Select.Content>
          </Select.Root>
        </Field.Field>

        <Field.Field>
          <Field.Label for="planner-recurrence">Repeat</Field.Label>
          <Select.Root
            type="single"
            value={recurrence}
            onValueChange={(value) => (recurrence = value ?? "none")}
          >
            <Select.Trigger id="planner-recurrence" class="w-full">
              <span class="capitalize"
                >{recurrence === "none" ? "Does not repeat" : recurrence}</span
              >
            </Select.Trigger>
            <Select.Content>
              <Select.Group>
                <Select.Item value="none" label="Does not repeat">
                  Does not repeat
                </Select.Item>
                <Select.Item value="daily" label="Daily">Daily</Select.Item>
                <Select.Item value="weekly" label="Weekly">Weekly</Select.Item>
                <Select.Item value="monthly" label="Monthly"
                  >Monthly</Select.Item
                >
              </Select.Group>
            </Select.Content>
          </Select.Root>
        </Field.Field>
      </div>

      {#if workspaceContext?.is_global && !activityProjectId}
        <Field.Field>
          <Field.Label for="planner-workspace">Company workspace</Field.Label>
          <Select.Root
            type="single"
            value={activityWorkspaceId}
            onValueChange={(value) => {
              activityWorkspaceId = value ?? "";
              activityTeamId = "";
              activityResourceId = "";
            }}
          >
            <Select.Trigger id="planner-workspace" class="w-full">
              <span class="truncate">
                {workspaceContext.workspaces.find(
                  (workspace) => workspace.id === activityWorkspaceId,
                )?.name ?? "Select workspace"}
              </span>
            </Select.Trigger>
            <Select.Content>
              <Select.Group>
                {#each workspaceContext.workspaces as workspace (workspace.id)}
                  <Select.Item value={workspace.id} label={workspace.name}>
                    {workspace.name}
                  </Select.Item>
                {/each}
              </Select.Group>
            </Select.Content>
          </Select.Root>
        </Field.Field>
      {:else if selectedComposerWorkspace}
        <p
          class="rounded-lg bg-muted/50 px-3 py-2 text-xs text-muted-foreground"
        >
          Company: {selectedComposerWorkspace.name}
        </p>
      {/if}

      <Field.Field>
        <Field.Label for="planner-project">Project (optional)</Field.Label>
        <Select.Root
          type="single"
          value={activityProjectId || "none"}
          onValueChange={(value) => {
            activityProjectId = value === "none" ? "" : (value ?? "");
            activityTeamId = "";
            activityResourceId = "";
          }}
        >
          <Select.Trigger id="planner-project" class="w-full">
            <span class="truncate">
              {projects.find((project) => project.id === activityProjectId)
                ?.name ?? "No project"}
            </span>
          </Select.Trigger>
          <Select.Content>
            <Select.Group>
              <Select.Item value="none" label="No project"
                >No project</Select.Item
              >
              {#each projects as project (project.id)}
                <Select.Item value={project.id} label={project.name}>
                  {project.name}
                </Select.Item>
              {/each}
            </Select.Group>
          </Select.Content>
        </Select.Root>
      </Field.Field>

      {#if teams.length > 0}
        <Field.Field>
          <Field.Label for="planner-team">Team (optional)</Field.Label>
          <Select.Root
            type="single"
            value={activityTeamId || "none"}
            onValueChange={(value) =>
              (activityTeamId = value === "none" ? "" : (value ?? ""))}
          >
            <Select.Trigger id="planner-team" class="w-full">
              <span
                >{teams.find((team) => team.id === activityTeamId)?.name ??
                  "No team"}</span
              >
            </Select.Trigger>
            <Select.Content>
              <Select.Group>
                <Select.Item value="none" label="No team">No team</Select.Item>
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

      <div class="grid gap-4 sm:grid-cols-2">
        <Field.Field>
          <Field.Label for="planner-start">Starts</Field.Label>
          <Input
            id="planner-start"
            type="datetime-local"
            bind:value={activityStartsAt}
          />
        </Field.Field>
        <Field.Field>
          <Field.Label for="planner-end">Ends</Field.Label>
          <Input
            id="planner-end"
            type="datetime-local"
            bind:value={activityEndsAt}
          />
        </Field.Field>
      </div>

      {#if recurrence !== "none"}
        <div class="grid gap-4 sm:grid-cols-2">
          <Field.Field>
            <Field.Label for="planner-interval">Repeat every</Field.Label>
            <Input
              id="planner-interval"
              type="number"
              min="1"
              max="52"
              bind:value={recurrenceInterval}
            />
          </Field.Field>
          <Field.Field>
            <Field.Label for="planner-until">Repeat through</Field.Label>
            <Input
              id="planner-until"
              type="date"
              bind:value={recurrenceUntil}
            />
          </Field.Field>
        </div>
      {/if}

      <Field.Field>
        <Field.Label for="planner-resource"
          >Reserve resource (optional)</Field.Label
        >
        <Select.Root
          type="single"
          value={activityResourceId || "none"}
          onValueChange={(value) =>
            (activityResourceId = value === "none" ? "" : (value ?? ""))}
        >
          <Select.Trigger id="planner-resource" class="w-full">
            <span class="truncate">
              {filteredResources.find(
                (resource) => resource.id === activityResourceId,
              )?.name ?? "No resource"}
            </span>
          </Select.Trigger>
          <Select.Content>
            <Select.Group>
              <Select.Item value="none" label="No resource"
                >No resource</Select.Item
              >
              {#each filteredResources as resource (resource.id)}
                <Select.Item value={resource.id} label={resource.name}>
                  {resource.name} · {resource.resource_type}
                </Select.Item>
              {/each}
            </Select.Group>
          </Select.Content>
        </Select.Root>
      </Field.Field>

      <Field.Field>
        <Field.Label for="planner-description"
          >Description (optional)</Field.Label
        >
        <Input id="planner-description" bind:value={activityDescription} />
      </Field.Field>
    </Field.FieldGroup>

    <Dialog.Footer>
      <Button variant="outline" onclick={() => (activityOpen = false)}>
        Cancel
      </Button>
      <Button disabled={activitySaving || !canManage} onclick={createActivity}>
        {activitySaving ? "Saving…" : "Create activity"}
      </Button>
    </Dialog.Footer>
  </Dialog.Content>
</Dialog.Root>

<style>
  .planner {
    animation: arrive 420ms cubic-bezier(0.2, 0.75, 0.25, 1) both;
  }

  .eyebrow {
    color: var(--muted-foreground);
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.14em;
    text-transform: uppercase;
  }

  .calendar-wrap {
    overflow-x: auto;
  }

  .calendar-grid {
    display: grid;
    min-width: 660px;
    grid-template-columns: repeat(7, minmax(0, 1fr));
  }

  .weekday-row {
    border-bottom: 1px solid var(--border);
    background: var(--muted);
  }

  .weekday-label {
    padding: 0.7rem 0.75rem;
    color: var(--muted-foreground);
    font-size: 0.63rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
  }

  .calendar-cell {
    position: relative;
    min-width: 0;
    min-height: 7.2rem;
    padding: 0.6rem 0.55rem 0.5rem;
    border-right: 1px solid var(--border);
    border-bottom: 1px solid var(--border);
    background: var(--card);
  }

  .calendar-cell:nth-child(7n) {
    border-right: 0;
  }

  .calendar-cell:hover {
    background: var(--muted);
  }

  .calendar-cell.outside {
    background: var(--background);
  }

  .calendar-cell.outside .day-number {
    color: var(--muted-foreground);
  }

  .calendar-cell.selected {
    z-index: 1;
    box-shadow: inset 0 0 0 2px var(--ring);
  }

  .day-number {
    display: inline-flex;
    width: 1.7rem;
    height: 1.7rem;
    align-items: center;
    justify-content: center;
    border-radius: 999px;
    color: var(--foreground);
    font-size: 0.75rem;
    font-weight: 600;
    font-variant-numeric: tabular-nums;
  }

  .calendar-cell.today .day-number {
    background: var(--primary);
    color: var(--primary-foreground);
  }

  .calendar-cell.selected .day-number {
    color: var(--foreground);
    font-weight: 800;
  }

  .calendar-cell.today.selected .day-number {
    background: var(--primary);
    color: var(--primary-foreground);
  }

  .task-indicators {
    display: flex;
    flex-direction: column;
    gap: 3px;
    margin-top: 0.28rem;
  }

  .task-pill {
    display: flex;
    min-width: 0;
    height: 1.2rem;
    align-items: center;
    gap: 0.3rem;
    overflow: hidden;
    border-radius: var(--radius-sm);
    padding: 0 0.25rem;
    background: color-mix(in oklab, var(--task-color) 38%, var(--card));
    color: var(--foreground);
    font-size: 0.6rem;
    line-height: 1;
  }

  .task-pill:hover {
    background: color-mix(in oklab, var(--task-color) 55%, var(--card));
  }

  .task-pill-dot {
    width: 0.32rem;
    height: 0.32rem;
    flex: 0 0 0.32rem;
    border-radius: 50%;
    background: var(--task-color);
  }

  .more-count {
    display: block;
    margin-top: 0.25rem;
    color: var(--muted-foreground);
    font-size: 0.58rem;
  }

  .loading-grid .calendar-cell {
    display: flex;
    align-items: flex-start;
    justify-content: flex-end;
    padding: 0.8rem;
  }

  .agenda-date {
    min-width: 3.2rem;
    background: color-mix(in oklab, var(--task-color) 10%, var(--card));
    color: var(--foreground);
  }

  .active-view {
    background: var(--card);
    color: var(--foreground);
    box-shadow: 0 1px 3px
      color-mix(in oklab, var(--foreground) 12%, transparent);
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

  @media (max-width: 639px) {
    .calendar-grid {
      min-width: 0;
    }

    .weekday-label {
      padding-inline: 0.25rem;
      text-align: center;
    }

    .calendar-cell {
      min-height: 4.65rem;
      padding: 0.28rem;
      text-align: center;
    }

    .day-number {
      width: 1.55rem;
      height: 1.55rem;
    }

    .task-indicators {
      min-height: 0.35rem;
      flex-direction: row;
      justify-content: center;
      gap: 2px;
      margin-top: 0.25rem;
    }

    .task-pill {
      width: 0.32rem;
      height: 0.32rem;
      padding: 0;
      background: var(--task-color);
    }

    .task-pill-dot {
      display: none;
    }

    .more-count {
      display: none;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .planner {
      animation: none;
    }
  }
</style>
