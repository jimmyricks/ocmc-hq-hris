<script lang="ts">
  import { browser } from "$app/environment";
  import { toast } from "$lib/notifications";
  import { taskApi } from "$lib/task-manager/api.js";
  import { refCache } from "$lib/task-manager/ref-cache.js";
  import { userApi } from "$lib/users/api.js";
  import type {
    ApprovalDecision,
    Comment,
    Project,
    ProjectMember,
    Task,
    TaskAssignment,
    TaskSubmission,
    TaskSummary,
    TaskType,
    TaskCategory,
    User,
    WorkflowProgress,
    WorkflowTransition,
  } from "$lib/task-manager/types.js";
  import { isProjectManager } from "$lib/auth";
  import { useAppState } from "$lib/app-state.svelte.js";
  import { OFFICIAL_CURRENCY } from "$lib/constants.js";
  import {
    PRIORITY_META,
    stateBadge,
    formatDueDate,
    taskState,
  } from "$lib/task-manager/utils.js";

  import * as Tabs from "$lib/components/ui/tabs/index.js";
  import * as Dialog from "$lib/components/ui/dialog/index.js";
  import * as Field from "$lib/components/ui/field/index.js";
  import * as Select from "$lib/components/ui/select/index.js";
  import * as DropdownMenu from "$lib/components/ui/dropdown-menu/index.js";
  import { Button } from "$lib/components/ui/button/index.js";
  import { Input } from "$lib/components/ui/input/index.js";
  import UserCombobox from "$lib/components/user-combobox.svelte";
  import SubmitWorkDialog from "$lib/components/task-manager/submit-work-dialog.svelte";
  import TaskCommentsTab from "$lib/components/task-manager/task-comments-tab.svelte";
  import { Textarea } from "$lib/components/ui/textarea/index.js";
  import { Badge } from "$lib/components/ui/badge/index.js";
  import { Skeleton } from "$lib/components/ui/skeleton/index.js";
  import { cn } from "$lib/utils.js";

  import PlayIcon from "@lucide/svelte/icons/play";
  import SendIcon from "@lucide/svelte/icons/send";
  import CheckIcon from "@lucide/svelte/icons/check";
  import XIcon from "@lucide/svelte/icons/x";
  import RefreshCwIcon from "@lucide/svelte/icons/refresh-cw";
  import LockIcon from "@lucide/svelte/icons/lock";
  import ExternalLinkIcon from "@lucide/svelte/icons/external-link";
  import MessageSquareIcon from "@lucide/svelte/icons/message-square";
  import Trash2Icon from "@lucide/svelte/icons/trash-2";
  import ClipboardListIcon from "@lucide/svelte/icons/clipboard-list";
  import SaveIcon from "@lucide/svelte/icons/save";
  import ChevronDownIcon from "@lucide/svelte/icons/chevron-down";

  interface Props {
    open?: boolean;
    presentation?: "modal" | "drawer";
    taskId: string | null;
    /** When set, the modal opens in "new task" create mode with these defaults. */
    newTask?: Task | null;
    projects?: Project[];
    taskTypes?: TaskType[];
    taskCategories?: TaskCategory[];
    members?: ProjectMember[];
    users?: User[];
    onTaskUpdated?: () => void;
    onTaskCreated?: (task: Task) => void;
    onTaskDeleted?: (id: string) => void;
  }

  let {
    open = $bindable(false),
    presentation = "modal",
    taskId,
    newTask = null,
    projects = [],
    taskTypes: taskTypesProp = [],
    taskCategories: taskCategoriesProp = [],
    members: membersProp = [],
    users: usersProp = [],
    onTaskUpdated,
    onTaskCreated,
    onTaskDeleted,
  }: Props = $props();

  const appState = useAppState();
  const currentUser = $derived(appState.user);
  const workspaceContext = $derived(appState.workspaceContext);
  let task = $state<Task | null>(null);
  let project = $state<Project | null>(null);
  let taskTypes = $state<TaskType[]>([]);
  let taskCategories = $state<TaskCategory[]>([]);
  let assignments = $state<TaskAssignment[]>([]);
  let submissions = $state<TaskSubmission[]>([]);
  let comments = $state<Comment[]>([]);
  let members = $state<ProjectMember[]>([]);
  let users = $state<User[]>([]);
  let workflowProgress = $state<WorkflowProgress | null>(null);
  let workflowActions = $state<WorkflowTransition[]>([]);
  let deliverable = $state<TaskSummary | null>(null);
  let loading = $state(true);
  let error = $state("");
  let activeTab = $state("details");

  // Create mode
  let isNew = $derived(!!newTask);
  let selectedAssigneeId = $state<string>("");
  let deleteConfirm = $state(false);

  // Editable draft of the task
  const emptyTask: Task = {
    id: "",
    project_id: "",
    task_type_id: "",
    title: "",
    status: "draft",
    priority: "medium",
  };
  let draft = $state<Task>({ ...emptyTask });
  let saving = $state(false);
  let dueDateInput = $state("");

  // Submit-work dialog
  let submitOpen = $state(false);
  let externalLink = $state("");
  let content = $state("");
  let notes = $state("");
  let submitting = $state(false);

  // Review dialog
  let reviewOpen = $state(false);
  let reviewDecision = $state<ApprovalDecision | "">("approved");
  let reviewRemarks = $state("");
  let reviewing = $state(false);
  let reviewSubmission = $state<TaskSubmission | null>(null);
  let transitionBusy = $state(false);

  let isPM = $derived(
    isProjectManager(currentUser) ||
      project?.manager_id === currentUser?.id ||
      members.some(
        (member) =>
          member.user_id === currentUser?.id &&
          member.role === "manager" &&
          member.is_active !== false,
      ) ||
      Boolean(
        workspaceContext?.can_manage &&
          (workspaceContext.is_global ||
            workspaceContext.active_workspace_id === project?.workspace_id),
      ),
  );
  let myAssignment = $derived(
    assignments.find(
      (a) => a.user_id === currentUser?.id && a.is_active !== false,
    ),
  );
  let isAssignee = $derived(!!myAssignment);

  let stateValue = $derived(task ? taskState(task) : null);
  let badge = $derived.by(() => {
    if (!task) return null;
    const meta = stateBadge({
      workflow_state: task.workflow_state,
      status: task.status,
    });
    return {
      ...meta,
      label: workflowProgress?.node?.current_state_label ?? meta.label,
    };
  });
  let isForReview = $derived(
    stateValue === "for_review" ||
      stateValue === "for_approval" ||
      stateValue === "submitted",
  );
  let isClosed = $derived(
    stateValue === "closed" ||
      stateValue === "done" ||
      stateValue === "cancelled",
  );
  let fieldsLocked = $derived(isForReview || isClosed);
  let taskTypeLocked = $derived(isClosed || stateValue === "approved");
  let submissionMode = $derived(
    taskTypes.find((tt) => tt.id === (draft.task_type_id || task?.task_type_id))
      ?.submission_mode ??
      deliverable?.submission_mode ??
      "link",
  );
  let submittedLinks = $derived(
    submissions
      .filter((submission) => Boolean(submission.external_link?.trim()))
      .sort(
        (a, b) =>
          Date.parse(b.submitted_at ?? b.created_at ?? "") -
          Date.parse(a.submitted_at ?? a.created_at ?? ""),
      ),
  );
  let reviewableSubmission = $derived(
    submissions.find(
      (s) => s.status === "submitted" || s.status === "under_review",
    ),
  );

  const decisionLabel: Record<ApprovalDecision, string> = {
    approved: "Approve",
    rejected: "Reject",
    needs_revision: "Request Revision",
  };

  let due = $derived(formatDueDate(draft.due_date));
  let priorityMeta = $derived(PRIORITY_META[draft.priority]);

  // Primary active assignee for existing tasks (first active assignment)
  let activeAssigneeId = $derived(
    assignments.find((a) => a.is_active !== false)?.user_id ?? "",
  );

  // Reset + load when taskId or newTask changes
  $effect(() => {
    if (!browser || !open) return;
    activeTab = "details";
    deleteConfirm = false;
    if (newTask) {
      // Create mode — use props for types/categories/users, no API load
      task = null;
      draft = { ...newTask };
      selectedAssigneeId = "";
      taskTypes = taskTypesProp;
      taskCategories = taskCategoriesProp;
      users = usersProp;
      members = membersProp;
      assignments = [];
      submissions = [];
      comments = [];
      loading = false;
      error = "";
      dueDateInput = newTask.due_date ? newTask.due_date.split("T")[0] : "";
    } else if (taskId) {
      load();
    }
  });

  function mergeUsers(...lists: User[][]): User[] {
    const merged = new Map<string, User>();
    for (const list of lists) {
      for (const user of list) merged.set(user.id, user);
    }
    return [...merged.values()];
  }

  async function load() {
    if (!taskId) return;
    loading = true;
    error = "";
    try {
      const t = await taskApi.getTask(taskId);
      if (!t) {
        error = "Task not found";
        return;
      }
      task = t;
      draft = { ...t };
      // Only fetch task-specific data (assignments, submissions, comments).
      // Reference data (users, task_types, task_categories) comes from props
      // or the shared ref-cache — no redundant API calls.
      const [a, subs, cmts, prog, del, types, cats] = await Promise.all([
        taskApi.getTaskAssignments(taskId).catch(() => [] as TaskAssignment[]),
        taskApi
          .getSubmissionsForTask(taskId)
          .catch(() => [] as TaskSubmission[]),
        taskApi.getComments(taskId).catch(() => [] as Comment[]),
        taskApi
          .getWorkflowProgress("task", taskId)
          .catch(() => null as WorkflowProgress | null),
        taskApi
          .getTaskDeliverable(taskId)
          .catch(() => null as TaskSummary | null),
        taskTypesProp.length > 0
          ? Promise.resolve(taskTypesProp)
          : refCache.getTaskTypes().catch(() => [] as TaskType[]),
        taskCategoriesProp.length > 0
          ? Promise.resolve(taskCategoriesProp)
          : refCache.getTaskCategories().catch(() => [] as TaskCategory[]),
      ]);
      assignments = a ?? [];
      selectedAssigneeId =
        assignments.find((assignment) => assignment.is_active !== false)
          ?.user_id ?? "";
      submissions = subs ?? [];
      comments = cmts ?? [];
      deliverable = del ?? null;
      users = mergeUsers(
        usersProp,
        currentUser ? [{ ...currentUser, is_active: true }] : [],
      );
      taskTypes = types ?? [];
      taskCategories = cats ?? [];
      workflowProgress = prog;
      workflowActions =
        prog?.node?.next_actions ??
        prog?.available_transitions ??
        (await taskApi
          .getAvailableWorkflowTransitions("task", taskState(t), taskId)
          .catch(() => [] as WorkflowTransition[]));
      project = projects.find((p) => p.id === t.project_id) ?? null;
      if (project?.id) {
        const projectMembers = membersProp.length
          ? membersProp
          : await taskApi
              .getProjectMembers(project.id)
              .catch(() => [] as ProjectMember[]);
        members = projectMembers;
      }
      dueDateInput = t.due_date ? t.due_date.split("T")[0] : "";
    } catch (err: any) {
      error = err.message || "Failed to load task";
    } finally {
      loading = false;
    }
  }

  function userName(id: string): string {
    const u = users.find((x) => x.id === id);
    return u ? u.full_name || u.email : id;
  }

  function searchAssignableUsers(search: string) {
    const projectId = draft.project_id || project?.id;
    if (!projectId) return Promise.resolve([]);
    return userApi.lookup({ search, projectId, pageSize: 5 });
  }

  function selectAssignee(user: User) {
    users = mergeUsers(users, [user]);
  }

  function userInitials(id: string): string {
    const name = userName(id);
    return name
      .split(" ")
      .map((p) => p[0])
      .filter(Boolean)
      .slice(0, 2)
      .join("")
      .toUpperCase();
  }

  function onDateChange(value: string) {
    dueDateInput = value;
    draft.due_date = value ? `${value}T00:00:00` : undefined;
  }

  async function handleSave() {
    saving = true;
    try {
      if (isNew) {
        const created = await taskApi.createTask({
          project_id: draft.project_id,
          task_type_id: draft.task_type_id,
          title: draft.title,
          category_id: draft.category_id,
          priority: draft.priority,
          due_date: draft.due_date,
          description: draft.description,
        });
        if (selectedAssigneeId) {
          await taskApi.assignTask(created.id, selectedAssigneeId);
        }
        toast.success("Task created");
        onTaskCreated?.(created);
        open = false;
      } else if (task) {
        await taskApi.updateTask(draft);
        if (selectedAssigneeId && selectedAssigneeId !== activeAssigneeId) {
          await taskApi.assignTask(task.id, selectedAssigneeId);
        }
        // Reload assignments, submissions, and workflow state — assignment
        // side-effects can change the task status.
        await load();
        toast.success("Task saved");
        onTaskUpdated?.();
      }
    } catch (err: any) {
      toast.error(err.message || "Failed to save task");
    } finally {
      saving = false;
    }
  }

  async function handleDelete() {
    if (!task) return;
    if (!deleteConfirm) {
      deleteConfirm = true;
      return;
    }
    try {
      await taskApi.deleteTask(task.id);
      toast.success("Task deleted");
      onTaskDeleted?.(task.id);
      open = false;
    } catch (err: any) {
      toast.error(err.message || "Failed to delete task");
    }
  }

  // --- Workflow actions ---
  const submissionActions = new Set([
    "submit",
    "submit_for_review",
    "submit_for_approval",
  ]);
  const reviewActionDecisions: Record<string, ApprovalDecision> = {
    approve: "approved",
    request_changes: "needs_revision",
    revise: "needs_revision",
    reject: "rejected",
  };

  function transitionDisabled(transition: WorkflowTransition): boolean {
    const action = transition.action_slug;
    if (submissionActions.has(action)) return !myAssignment;
    if (action in reviewActionDecisions) return !reviewableSubmission;
    return false;
  }

  async function handleWorkflowAction(transition: WorkflowTransition) {
    if (!task || transitionDisabled(transition)) return;
    const action = transition.action_slug;
    if (submissionActions.has(action)) {
      openSubmit();
      return;
    }
    if (action in reviewActionDecisions && reviewableSubmission) {
      openReview(reviewableSubmission, reviewActionDecisions[action]);
      return;
    }

    transitionBusy = true;
    try {
      await taskApi.executeWorkflowTransition("task", {
        record_id: task.id,
        action,
      });
      toast.success(transition.action_label || "Status updated");
      await load();
      onTaskUpdated?.();
    } catch (err: any) {
      toast.error(err.message || "Failed to update task status");
    } finally {
      transitionBusy = false;
    }
  }

  function openSubmit() {
    // Revisions keep the current deliverable link; assignees change it only
    // when they intend to replace the task's link.
    externalLink = deliverable?.deliverable_url ?? "";
    content = "";
    notes = "";
    submitOpen = true;
  }

  async function handleSubmit() {
    if (!myAssignment) return;
    submitting = true;
    try {
      const latestRevision = submissions.find(
        (s) => s.status === "needs_revision",
      );
      await taskApi.submitWork({
        task_assignment_id: myAssignment.id,
        notes: notes || undefined,
        external_link:
          submissionMode === "text" ? undefined : externalLink || undefined,
        content: submissionMode === "text" ? content || undefined : undefined,
        previous_submission_id: latestRevision?.id,
      });
      submitOpen = false;
      toast.success("Work submitted for review");
      await load();
      onTaskUpdated?.();
    } catch (err: any) {
      toast.error(err.message || "Failed to submit work");
    } finally {
      submitting = false;
    }
  }

  function openReview(
    submission: TaskSubmission,
    decision: ApprovalDecision = "approved",
  ) {
    reviewSubmission = submission;
    reviewDecision = decision;
    reviewRemarks = "";
    reviewOpen = true;
  }

  async function handleReview() {
    if (!reviewSubmission || !reviewDecision) return;
    if (reviewDecision !== "approved" && !reviewRemarks.trim()) {
      toast.error("Remarks are required for reject or revision requests");
      return;
    }
    reviewing = true;
    try {
      await taskApi.approveSubmission(
        reviewSubmission.id,
        reviewDecision,
        reviewRemarks || undefined,
      );
      reviewOpen = false;
      toast.success("Review submitted");
      await load();
      onTaskUpdated?.();
    } catch (err: any) {
      toast.error(err.message || "Review failed");
    } finally {
      reviewing = false;
    }
  }

  const componentId = $props.id();
  const drawerToggleId = `task-detail-drawer-${componentId}`;

  function handleDrawerKeydown(event: KeyboardEvent) {
    if (event.key === "Escape" && presentation === "drawer" && open)
      open = false;
  }
</script>

<svelte:window onkeydown={handleDrawerKeydown} />

{#snippet detailBody()}
  {#if loading}
    <Dialog.Header>
      <Dialog.Title>Loading task...</Dialog.Title>
    </Dialog.Header>
    <div class="space-y-4 py-2">
      <Skeleton class="h-8 w-2/3" />
      <Skeleton class="h-64 w-full" />
    </div>
  {:else if error}
    <Dialog.Header>
      <Dialog.Title>{error}</Dialog.Title>
      <Dialog.Description>The task may have been removed.</Dialog.Description>
    </Dialog.Header>
  {:else if task || isNew}
    <Tabs.Root bind:value={activeTab}>
      <Dialog.Header class="mb-0!">
        <div>
          {#if isNew}
            <Dialog.Title>New Task</Dialog.Title>
            <Dialog.Description
              >Create a new task and assign it to a project member.</Dialog.Description
            >
          {:else}
            <div class="flex items-center gap-2.5">
              <Dialog.Title class="flex min-w-0 flex-1 items-center gap-2">
                {#if project}
                  <span
                    class="size-2 shrink-0 rounded-full"
                    style:background-color={project.color ??
                      "var(--color-base-content)"}
                  ></span>
                  <span class="truncate">{project.name}</span>
                {:else}
                  Task
                {/if}
              </Dialog.Title>
              {#if fieldsLocked || taskTypeLocked}
                <Badge variant="secondary" class="gap-1" size="xl">
                  <LockIcon class="size-3" />
                  {isForReview ? "Locked for review" : ""}
                </Badge>
              {/if}

              {#if task!.task_key}
                <span class="shrink-0 font-mono text-sm text-base-content/60"
                  >{task!.task_key}</span
                >
              {/if}
              <DropdownMenu.DropdownMenu>
                <DropdownMenu.DropdownMenuTrigger
                  class="btn btn-outline border-base-300 btn-sm gap-2 px-3 font-medium"
                  role="button"
                >
                  <span
                    class="size-2 rounded-full"
                    style:background-color={badge?.color ||
                      "var(--color-base-content)"}
                  ></span>
                  {badge?.label}
                  <ChevronDownIcon class="size-4 opacity-60" />
                </DropdownMenu.DropdownMenuTrigger>
                <DropdownMenu.DropdownMenuContent class="w-56" align="end">
                  {#if workflowActions.length === 0}
                    <DropdownMenu.DropdownMenuItem disabled>
                      No actions available
                    </DropdownMenu.DropdownMenuItem>
                  {:else}
                    {#each workflowActions as transition}
                      <DropdownMenu.DropdownMenuItem
                        disabled={transitionBusy ||
                          transitionDisabled(transition)}
                        onclick={() => handleWorkflowAction(transition)}
                      >
                        {#if submissionActions.has(transition.action_slug)}
                          <SendIcon class="size-4" />
                        {:else if transition.action_slug === "approve"}
                          <CheckIcon class="size-4" />
                        {:else if transition.action_slug === "reject"}
                          <XIcon class="size-4" />
                        {:else if transition.action_slug === "request_changes" || transition.action_slug === "revise"}
                          <RefreshCwIcon class="size-4" />
                        {:else if transition.to_state === "done" || transition.to_state === "closed"}
                          <LockIcon class="size-4" />
                        {:else}
                          <PlayIcon class="size-4" />
                        {/if}
                        <span>{transition.action_label}</span>
                        {#if transition.to_state_label}
                          <span class="ml-auto text-xs text-base-content/50">
                            → {transition.to_state_label}
                          </span>
                        {/if}
                      </DropdownMenu.DropdownMenuItem>
                    {/each}
                  {/if}
                </DropdownMenu.DropdownMenuContent>
              </DropdownMenu.DropdownMenu>
            </div>
          {/if}
        </div>

        <Tabs.List
          size="sm"
          class={cn(
            "mt-2 w-full",
            isNew ? "grid grid-cols-1" : "grid grid-cols-2 sm:flex",
          )}
        >
          <Tabs.Trigger value="details" class="gap-1.5">
            <ClipboardListIcon class="size-4" />
            Details
          </Tabs.Trigger>
          {#if !isNew}
            <Tabs.Trigger value="comments" class="gap-1.5">
              <MessageSquareIcon class="size-4" />
              Comments
              {#if comments.length}
                <span class="ml-1 text-xs text-base-content/60"
                  >{comments.length}</span
                >
              {/if}
            </Tabs.Trigger>
          {/if}
        </Tabs.List>
      </Dialog.Header>

      <!-- DETAILS TAB -->
      <Tabs.Content value="details" class="space-y-2">
        {#if task || isNew}
          <Field.FieldGroup class="gap-4">
            <!-- Title -->
            <Field.Field class="gap-1">
              <Field.Label for="task-title">Title</Field.Label>
              <Input
                id="task-title"
                bind:value={draft.title}
                placeholder="Enter task title"
                size="md"
                class="w-full"
                disabled={fieldsLocked}
              />
            </Field.Field>

            <!-- Description -->
            <Field.Field class="gap-1">
              <Field.Label for="task-description">Description</Field.Label>
              <Textarea
                id="task-description"
                bind:value={draft.description}
                placeholder="Add details..."
                class="min-h-[80px] resize-none"
                disabled={fieldsLocked}
              />
            </Field.Field>

            <div class="grid grid-cols-2 gap-4">
              <!-- Task Type -->
              <Field.Field class="gap-1">
                <Field.Label for="task-type">Task Type</Field.Label>
                <Select.Root
                  type="single"
                  value={draft.task_type_id}
                  disabled={taskTypeLocked || taskTypes.length === 0}
                  onValueChange={(v) => {
                    draft.task_type_id = v;
                  }}
                >
                  <Select.Trigger id="task-type" size="md" class="w-full">
                    <span class="truncate">
                      {taskTypes.find((tt) => tt.id === draft.task_type_id)
                        ?.name ?? "Select..."}
                    </span>
                  </Select.Trigger>
                  <Select.Content class="p-1">
                    <Select.Group>
                      {#each taskTypes as tt (tt.id)}
                        <Select.Item value={tt.id} label={tt.name}>
                          {tt.name}
                          {#if tt.unit_rate}
                            <span class="ml-1 text-xs text-base-content/60">
                              ({new Intl.NumberFormat("en-PH", {
                                style: "currency",
                                currency: OFFICIAL_CURRENCY,
                              }).format(tt.unit_rate)}/{tt.unit})
                            </span>
                          {/if}
                        </Select.Item>
                      {/each}
                    </Select.Group>
                  </Select.Content>
                </Select.Root>
              </Field.Field>

              <!-- Priority -->
              <Field.Field class="gap-1">
                <Field.Label for="task-priority">Priority</Field.Label>
                <Select.Root
                  type="single"
                  value={draft.priority}
                  onValueChange={(v) => {
                    draft.priority = v as any;
                  }}
                >
                  <Select.Trigger id="task-priority" size="md" class="w-full">
                    {@const pmeta = PRIORITY_META[draft.priority]}
                    <span class="flex items-center gap-2">
                      <span
                        class="size-2 rounded-full"
                        style:background-color={pmeta.color}
                      ></span>
                      {pmeta.label}
                    </span>
                  </Select.Trigger>
                  <Select.Content class="p-1">
                    {#each Object.keys(PRIORITY_META) as priority (priority)}
                      {@const pmeta =
                        PRIORITY_META[priority as keyof typeof PRIORITY_META]}
                      <Select.Item value={priority} label={pmeta.label}>
                        <span class="flex items-center gap-2">
                          <span
                            class="size-2 rounded-full"
                            style:background-color={pmeta.color}
                          ></span>
                          {pmeta.label}
                        </span>
                      </Select.Item>
                    {/each}
                  </Select.Content>
                </Select.Root>
              </Field.Field>
            </div>

            <div class="grid grid-cols-2 gap-4">
              <!-- Due Date -->
              <Field.Field class="gap-1">
                <Field.Label for="task-due">Due Date</Field.Label>
                <Input
                  id="task-due"
                  type="date"
                  bind:value={dueDateInput}
                  oninput={(event) => onDateChange(event.currentTarget.value)}
                />
              </Field.Field>

              <!-- Assigned To -->
              <Field.Field class="gap-1">
                <Field.Label for="task-assignee">Assigned To</Field.Label>
                {#if isNew}
                  <UserCombobox
                    id="task-assignee"
                    bind:value={selectedAssigneeId}
                    selectedLabel={selectedAssigneeId
                      ? userName(selectedAssigneeId)
                      : ""}
                    fetchOptions={searchAssignableUsers}
                    onSelect={selectAssignee}
                    placeholder="Search project members..."
                  />
                {:else}
                  <UserCombobox
                    id="task-assignee"
                    bind:value={selectedAssigneeId}
                    selectedLabel={selectedAssigneeId
                      ? userName(selectedAssigneeId)
                      : ""}
                    fetchOptions={searchAssignableUsers}
                    onSelect={selectAssignee}
                    disabled={fieldsLocked || !isPM || saving}
                    placeholder={selectedAssigneeId
                      ? "Search project members..."
                      : "Unassigned"}
                  />
                {/if}
              </Field.Field>
            </div>
          </Field.FieldGroup>

          <section class="space-y-2" aria-labelledby="deliverable-heading">
            <h3 id="deliverable-heading" class="text-sm font-semibold">
              Deliverable
            </h3>
            {#if deliverable?.has_deliverable}
              {#if deliverable.deliverable_content}
                <div
                  class="rounded-lg border border-base-300 bg-base-200/50 px-3 py-2 text-sm whitespace-pre-wrap"
                >
                  {deliverable.deliverable_content}
                </div>
              {:else if deliverable.deliverable_url}
                <a
                  class="flex min-w-0 items-center gap-2 rounded-lg border border-base-300 px-3 py-2 text-sm hover:bg-base-200"
                  href={deliverable.deliverable_url}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  <ExternalLinkIcon class="size-4 shrink-0" />
                  <span class="min-w-0 flex-1 truncate">
                    {deliverable.deliverable_url}
                  </span>
                </a>
              {/if}
            {:else}
              <p class="text-sm text-base-content/60">
                No deliverable has been submitted yet.
              </p>
            {/if}

            {#if submittedLinks.length > 1}
              <h4 class="pt-2 text-xs font-semibold text-base-content/60">
                Submission history
              </h4>
              <ul class="space-y-2">
                {#each submittedLinks as submission (submission.id)}
                  <li>
                    <a
                      class="flex min-w-0 items-center gap-2 rounded-lg border border-base-300 px-3 py-2 text-sm hover:bg-base-200"
                      href={submission.external_link}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      <ExternalLinkIcon class="size-4 shrink-0" />
                      <span class="min-w-0 flex-1 truncate">
                        {submission.external_link}
                      </span>
                      <span class="shrink-0 text-xs text-base-content/60">
                        Version {submission.version ?? 1}
                      </span>
                    </a>
                  </li>
                {/each}
              </ul>
            {/if}
          </section>
        {/if}
      </Tabs.Content>

      {#if !isNew}
        <!-- COMMENTS TAB -->
        <Tabs.Content value="comments" class="space-y-4 pt-4">
          <TaskCommentsTab
            taskId={taskId ?? ""}
            bind:comments
            {users}
            currentUser={currentUser as User | null}
          />
        </Tabs.Content>
      {/if}
    </Tabs.Root>
  {/if}
{/snippet}

{#snippet detailFooter(footerClass: string)}
  {#if (task || isNew) && !loading && !error && activeTab !== "comments"}
    <Dialog.Footer class={cn("gap-2", footerClass)}>
      {#if !isNew}
        <div class="flex-1">
          <Button
            variant="outline"
            size="md"
            class={cn(
              "text-error hover:text-error hover:bg-error/10",
              deleteConfirm && "bg-error/10",
            )}
            onclick={handleDelete}
          >
            <Trash2Icon class="size-4" />
            {deleteConfirm ? "Click again to confirm" : ""}
          </Button>
        </div>
      {/if}
      <div class="flex gap-2 {isNew ? 'w-full justify-end' : ''}">
        <Button variant="outline" onclick={() => (open = false)} size="md"
          >Cancel</Button
        >
        <Button
          onclick={handleSave}
          disabled={saving || (!isNew && isClosed)}
          size="md"
          class="gap-1.5"
        >
          <SaveIcon class="size-4" />
          {saving
            ? isNew
              ? "Creating..."
              : "Saving..."
            : isNew
              ? "Create Task"
              : "Save Changes"}
        </Button>
      </div></Dialog.Footer
    >
  {/if}
{/snippet}

{#if presentation === "drawer"}
  <div class="drawer drawer-end">
    <input
      id={drawerToggleId}
      type="checkbox"
      class="drawer-toggle"
      bind:checked={open}
    />
    <div class="drawer-side z-50">
      <label
        for={drawerToggleId}
        aria-label="Close task details"
        class="drawer-overlay"
      ></label>
      <div
        class="relative flex h-full min-h-full w-screen flex-col bg-base-100 text-base-content shadow-xl sm:w-[42rem]"
      >
        <div class="min-h-0 flex-1 overflow-y-auto p-5">
          {@render detailBody()}
        </div>
        {@render detailFooter(
          "mt-0 shrink-0 border-t border-base-300 bg-base-100 px-5 py-4",
        )}
      </div>
    </div>
  </div>
{:else}
  <Dialog.Root bind:open>
    <Dialog.Content class="max-h-[90vh] overflow-y-auto max-w-xl!">
      {@render detailBody()}
      {@render detailFooter("")}
    </Dialog.Content>
  </Dialog.Root>
{/if}

<SubmitWorkDialog
  bind:open={submitOpen}
  taskTitle={task?.title ?? ""}
  {submissionMode}
  bind:externalLink
  bind:content
  bind:notes
  {submitting}
  onSubmit={handleSubmit}
/>

<!-- Review dialog -->
<Dialog.Root bind:open={reviewOpen}>
  <Dialog.Content class="max-w-lg">
    <Dialog.Header>
      <Dialog.Title>Review Submission</Dialog.Title>
      <Dialog.Description>
        Version {reviewSubmission?.version ?? 1} — choose an action below.
      </Dialog.Description>
    </Dialog.Header>
    <Field.FieldGroup>
      <Field.Field>
        <Field.Label>Decision</Field.Label>
        <form class="filter">
          <input
            class="btn btn-square"
            type="reset"
            value="×"
            aria-label="Reset decision"
            onclick={() => (reviewDecision = "")}
          />
          {#each Object.entries(decisionLabel) as [ApprovalDecision, string][] as [value, label] (value)}
            <input
              class="btn"
              type="radio"
              name="review-decision"
              {value}
              bind:group={reviewDecision}
              aria-label={label}
            />
          {/each}
        </form>
      </Field.Field>
      <Field.Field>
        <Field.Label for="review-remarks">Remarks</Field.Label>
        <Textarea
          id="review-remarks"
          bind:value={reviewRemarks}
          placeholder="Feedback for the worker..."
          class="min-h-[100px]"
        />
      </Field.Field>
    </Field.FieldGroup>
    <Dialog.Footer>
      <Button variant="outline" onclick={() => (reviewOpen = false)}
        >Cancel</Button
      >
      <Button
        disabled={reviewing || !reviewDecision}
        onclick={handleReview}
        class="gap-1.5"
      >
        {#if reviewDecision === "approved"}
          <CheckIcon class="size-4" />
        {:else if reviewDecision === "rejected"}
          <XIcon class="size-4" />
        {:else}
          <RefreshCwIcon class="size-4" />
        {/if}
        {reviewing
          ? "Submitting..."
          : reviewDecision
            ? decisionLabel[reviewDecision]
            : "Select a decision"}
      </Button>
    </Dialog.Footer>
  </Dialog.Content>
</Dialog.Root>
