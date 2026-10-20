<script lang="ts">
  import { browser } from "$app/environment";
  import { toast } from "svelte-sonner";
  import { taskApi } from "$lib/task-manager/api.js";
  import { refCache } from "$lib/task-manager/ref-cache.js";
  import type {
    ApprovalDecision,
    Comment,
    Project,
    ProjectMember,
    Task,
    TaskAssignment,
    TaskSubmission,
    TaskType,
    TaskCategory,
    User,
  } from "$lib/task-manager/types.js";
  import { getUser, isProjectManager, type User as AuthUser } from "$lib/auth";
  import { workspaceApi } from "$lib/workspaces/api";
  import type { WorkspaceContext } from "$lib/workspaces/types";
  import { OFFICIAL_CURRENCY } from "$lib/constants.js";
  import {
    PRIORITY_META,
    STATUS_META,
    stateBadge,
    formatDueDate,
    timeAgo,
    taskState,
  } from "$lib/task-manager/utils.js";

  import * as Card from "$lib/components/ui/card/index.js";
  import * as Tabs from "$lib/components/ui/tabs/index.js";
  import * as Dialog from "$lib/components/ui/dialog/index.js";
  import * as Field from "$lib/components/ui/field/index.js";
  import * as InputGroup from "$lib/components/ui/input-group/index.js";
  import * as Select from "$lib/components/ui/select/index.js";
  import * as Popover from "$lib/components/ui/popover/index.js";
  import * as DropdownMenu from "$lib/components/ui/dropdown-menu/index.js";
  import { Button } from "$lib/components/ui/button/index.js";
  import { Input } from "$lib/components/ui/input/index.js";
  import { Textarea } from "$lib/components/ui/textarea/index.js";
  import { Badge } from "$lib/components/ui/badge/index.js";
  import { Separator } from "$lib/components/ui/separator/index.js";
  import { Avatar, AvatarFallback } from "$lib/components/ui/avatar/index.js";
  import * as Empty from "$lib/components/ui/empty/index.js";
  import * as Item from "$lib/components/ui/item/index.js";
  import { ScrollAreaScrollbar } from "$lib/components/ui/scroll-area/index.js";
  import { ScrollArea as ScrollAreaPrimitive } from "bits-ui";
  import { Skeleton } from "$lib/components/ui/skeleton/index.js";
  import CalendarPicker from "$lib/components/ui/calendar/calendar.svelte";
  import { parseDate, type DateValue } from "@internationalized/date";
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
  import CalendarIcon from "@lucide/svelte/icons/calendar";
  import SaveIcon from "@lucide/svelte/icons/save";
  import PlusIcon from "@lucide/svelte/icons/plus";
  import EllipsisIcon from "@lucide/svelte/icons/ellipsis";
  import PencilIcon from "@lucide/svelte/icons/pencil";

  interface Props {
    open?: boolean;
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
    taskId,
    newTask = null,
    projects = [],
    taskTypes: taskTypesProp = [],
    taskCategories: taskCategoriesProp = [],
    members = [],
    users: usersProp = [],
    onTaskUpdated,
    onTaskCreated,
    onTaskDeleted,
  }: Props = $props();

  let currentUser = $state<AuthUser | null>(null);
  let workspaceContext = $state<WorkspaceContext | null>(null);
  let task = $state<Task | null>(null);
  let project = $state<Project | null>(null);
  let taskTypes = $state<TaskType[]>([]);
  let taskCategories = $state<TaskCategory[]>([]);
  let assignments = $state<TaskAssignment[]>([]);
  let submissions = $state<TaskSubmission[]>([]);
  let comments = $state<Comment[]>([]);
  let users = $state<User[]>([]);
  let loading = $state(true);
  let error = $state("");
  let activeTab = $state("details");

  // Create mode
  let isNew = $derived(!!newTask);
  let assigneeId = $state<string>("");
  let deleteConfirm = $state(false);

  // Editable draft of the task
  const emptyTask: Task = {
    id: "",
    project_id: "",
    task_type_id: "",
    title: "",
    status: "pending",
    priority: "medium",
  };
  let draft = $state<Task>({ ...emptyTask });
  let saving = $state(false);
  let dateOpen = $state(false);
  let calendarValue: DateValue[] = $state([]);

  // Submit-work dialog
  let submitOpen = $state(false);
  let externalLink = $state("");
  let notes = $state("");
  let submitting = $state(false);

  // Review dialog
  let reviewOpen = $state(false);
  let reviewDecision = $state<ApprovalDecision>("approved");
  let reviewRemarks = $state("");
  let reviewing = $state(false);
  let reviewSubmission = $state<TaskSubmission | null>(null);

  // Comment composer
  let commentBody = $state("");
  let commentSending = $state(false);
  let editingCommentId = $state<string | null>(null);
  let editBody = $state("");

  let isPM = $derived(
    isProjectManager(currentUser) ||
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

  // Assignable users for create mode = project members of selected project
  let assignableUsers = $derived(
    members
      .filter((m) => m.project_id === draft.project_id)
      .map((m) => users.find((u) => u.id === m.user_id))
      .filter((u): u is User => !!u),
  );

  let stateValue = $derived(task ? taskState(task) : null);
  let badge = $derived(
    task
      ? stateBadge({ workflow_state: task.workflow_state, status: task.status })
      : null,
  );
  let isForReview = $derived(stateValue === "for_review");
  let isClosed = $derived(stateValue === "closed");
  let fieldsLocked = $derived(isForReview || isClosed);

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
    currentUser = getUser();
    workspaceApi
      .getContext()
      .then((context) => (workspaceContext = context))
      .catch(() => (workspaceContext = null));
    activeTab = "details";
    deleteConfirm = false;
    if (newTask) {
      // Create mode — use props for types/categories/users, no API load
      task = null;
      draft = { ...newTask };
      assigneeId = "";
      taskTypes = taskTypesProp;
      taskCategories = taskCategoriesProp;
      users = usersProp;
      assignments = [];
      submissions = [];
      comments = [];
      loading = false;
      error = "";
      const datePart = newTask.due_date
        ? newTask.due_date.split("T")[0]
        : undefined;
      const parsed = datePart ? parseDate(datePart) : undefined;
      calendarValue = parsed ? [parsed] : [];
    } else if (taskId) {
      load();
    }
  });

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
      const [a, subs, cmts, usrs, types, cats] = await Promise.all([
        taskApi.getTaskAssignments(taskId).catch(() => [] as TaskAssignment[]),
        taskApi
          .getSubmissionsForTask(taskId)
          .catch(() => [] as TaskSubmission[]),
        taskApi.getComments(taskId).catch(() => [] as Comment[]),
        usersProp.length > 0
          ? Promise.resolve(usersProp)
          : refCache.getUsers().catch(() => [] as User[]),
        taskTypesProp.length > 0
          ? Promise.resolve(taskTypesProp)
          : refCache.getTaskTypes().catch(() => [] as TaskType[]),
        taskCategoriesProp.length > 0
          ? Promise.resolve(taskCategoriesProp)
          : refCache.getTaskCategories().catch(() => [] as TaskCategory[]),
      ]);
      assignments = a ?? [];
      submissions = subs ?? [];
      comments = cmts ?? [];
      users = usrs ?? [];
      taskTypes = types ?? [];
      taskCategories = cats ?? [];
      project = projects.find((p) => p.id === t.project_id) ?? null;
      const datePart = t.due_date ? t.due_date.split("T")[0] : undefined;
      const parsed = datePart ? parseDate(datePart) : undefined;
      calendarValue = parsed ? [parsed] : [];
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

  function onDateChange(v: DateValue[] | undefined) {
    calendarValue = v ?? [];
    const selected = calendarValue[0];
    // Backend expects a full datetime; CalendarDate.toString() returns date-only ("2026-07-24").
    draft.due_date = selected ? `${selected.toString()}T00:00:00` : undefined;
    dateOpen = false;
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
        if (assigneeId) {
          await taskApi.assignTask(created.id, assigneeId);
        }
        toast.success("Task created");
        onTaskCreated?.(created);
        open = false;
      } else if (task) {
        const updated = await taskApi.updateTask(draft);
        task = updated;
        draft = { ...updated };
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
  async function startTask() {
    if (!task) return;
    try {
      await taskApi.executeWorkflowTransition("task", {
        record_id: task.id,
        action: "start",
      });
      toast.success("Task started");
      await load();
      onTaskUpdated?.();
    } catch (err: any) {
      toast.error(err.message || "Failed to start task");
    }
  }

  async function closeTask() {
    if (!task) return;
    try {
      await taskApi.executeWorkflowTransition("task", {
        record_id: task.id,
        action: "close",
      });
      toast.success("Task closed");
      await load();
      onTaskUpdated?.();
    } catch (err: any) {
      toast.error(err.message || "Failed to close task");
    }
  }

  function openSubmit() {
    externalLink = "";
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
        external_link: externalLink || undefined,
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

  function openReview(submission: TaskSubmission) {
    reviewSubmission = submission;
    reviewDecision = "approved";
    reviewRemarks = "";
    reviewOpen = true;
  }

  async function handleReview() {
    if (!reviewSubmission) return;
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

  // --- Comments ---
  async function sendComment() {
    if (!commentBody.trim() || !taskId) return;
    commentSending = true;
    try {
      const created = await taskApi.addComment(taskId, commentBody.trim());
      comments = [...comments, created];
      commentBody = "";
    } catch (err: any) {
      toast.error(err.message || "Failed to add comment");
    } finally {
      commentSending = false;
    }
  }

  async function deleteComment(commentId: string) {
    if (!taskId) return;
    try {
      await taskApi.deleteComment(taskId, commentId);
      comments = comments.filter((c) => c.id !== commentId);
    } catch (err: any) {
      toast.error(err.message || "Failed to delete comment");
    }
  }

  function startEditComment(commentId: string, body: string) {
    editingCommentId = commentId;
    editBody = body;
  }

  function cancelEditComment() {
    editingCommentId = null;
    editBody = "";
  }

  async function saveEditComment(commentId: string) {
    if (!taskId || !editBody.trim()) return;
    try {
      const updated = await taskApi.updateComment(
        taskId,
        commentId,
        editBody.trim(),
      );
      comments = comments.map((c) => (c.id === commentId ? updated : c));
      editingCommentId = null;
      editBody = "";
    } catch (err: any) {
      toast.error(err.message || "Failed to edit comment");
    }
  }

  // --- Links ---
  let newLinkUrl = $state("");

  function addLink(url: string) {
    const trimmed = url.trim();
    if (!trimmed) return;
    if (!draft.links) {
      draft.links = [];
    }
    draft.links = [
      ...draft.links,
      {
        id: crypto.randomUUID(),
        task_id: draft.id,
        url: trimmed,
      },
    ];
    newLinkUrl = "";
  }

  function removeLink(id: string) {
    if (!draft.links) return;
    draft.links = draft.links.filter((l) => l.id !== id);
  }
</script>

<Dialog.Root bind:open>
  <Dialog.Content class="max-h-[90vh] overflow-y-auto !max-w-xl p-4!">
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
        <Dialog.Header>
          <div class="flex flex-col justify-between">
            {#if isNew}
              <Dialog.Title>New Task</Dialog.Title>
              <Dialog.Description
                >Create a new task and assign it to a project member.</Dialog.Description
              >
            {:else}
              <div class="flex items-center gap-2">
                {#if task!.task_key}
                  <span class="font-mono text-sm text-muted-foreground"
                    >{task!.task_key}</span
                  >
                {/if}
                {#if fieldsLocked}
                  <span
                    class="inline-flex items-center gap-1 text-xs text-muted-foreground"
                  >
                    <LockIcon class="size-3" />
                    Locked for review
                  </span>
                {/if}
              </div>
              <Dialog.Title class="text-xl">{task!.title}</Dialog.Title>
              {#if project}
                <Dialog.Description
                  class="flex items-center gap-2 mt-2 justify-between"
                >
                  <DropdownMenu.DropdownMenu>
                    <DropdownMenu.DropdownMenuTrigger>
                      <Button
                        variant={badge?.variant || "default"}
                        class="gap-2 h-7 rounded-xl text-sm font-medium px-3"
                      >
                        <span
                          class="size-2 rounded-full"
                          style:background-color={badge?.color || "#6b7280"}
                        ></span>
                        {badge?.label}
                      </Button>
                    </DropdownMenu.DropdownMenuTrigger>
                    <DropdownMenu.DropdownMenuContent class="w-48">
                      {#if isAssignee && stateValue === "draft_assigned"}
                        <DropdownMenu.DropdownMenuItem onclick={startTask}>
                          <PlayIcon class="size-4" />
                          Start
                        </DropdownMenu.DropdownMenuItem>
                      {/if}
                      {#if isAssignee && (stateValue === "in_progress" || stateValue === "needs_revision")}
                        <DropdownMenu.DropdownMenuItem onclick={openSubmit}>
                          <SendIcon class="size-4" />
                          Submit Work
                        </DropdownMenu.DropdownMenuItem>
                      {/if}
                      {#if isPM && stateValue === "approved"}
                        <DropdownMenu.DropdownMenuItem onclick={closeTask}>
                          <LockIcon class="size-4" />
                          Close Task
                        </DropdownMenu.DropdownMenuItem>
                      {/if}
                    </DropdownMenu.DropdownMenuContent>
                  </DropdownMenu.DropdownMenu>
                  <div class="flex items-center gap-2">
                    <span
                      class="size-2 rounded-full"
                      style:background-color={project.color ?? "#6b7280"}
                    ></span>
                    {project.name}
                  </div>
                </Dialog.Description>
              {/if}
            {/if}
          </div>

          <Tabs.List
            class={cn(
              "grid w-full",
              isNew ? "grid-cols-1" : "grid-cols-2",
              "mt-2",
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
                  <span class="ml-1 text-xs text-muted-foreground"
                    >{comments.length}</span
                  >
                {/if}
              </Tabs.Trigger>
            {/if}
          </Tabs.List>
        </Dialog.Header>

        <!-- DETAILS TAB -->
        <Tabs.Content value="details" class="space-y-6 pt-2">
          {#if task || isNew}
            <Field.FieldGroup class="gap-4">
              <!-- Title -->
              <Field.Field class="gap-1">
                <Field.Label for="task-title">Title</Field.Label>
                <Input
                  id="task-title"
                  bind:value={draft.title}
                  placeholder="Enter task title"
                  class="w-full h-9"
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
                    disabled={fieldsLocked || taskTypes.length === 0}
                    onValueChange={(v) => {
                      draft.task_type_id = v;
                    }}
                  >
                    <Select.Trigger id="task-type" class="w-full !h-9">
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
                              <span class="ml-1 text-xs text-muted-foreground">
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
                    <Select.Trigger id="task-priority" class="w-full !h-9">
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
                  <Popover.Root bind:open={dateOpen}>
                    <Popover.Trigger>
                      {#snippet child({ props }: { props: any })}
                        <Button
                          {...props}
                          id="task-due"
                          variant="outline"
                          class={cn(
                            "w-full justify-start text-left font-normal h-9",
                            !draft.due_date && "text-muted-foreground",
                          )}
                        >
                          <CalendarIcon class="mr-2 size-4" />
                          {draft.due_date
                            ? draft.due_date.split("T")[0]
                            : "Pick a date"}
                        </Button>
                      {/snippet}
                    </Popover.Trigger>
                    <Popover.Content class="w-auto p-0" align="start">
                      <CalendarPicker
                        type="multiple"
                        value={calendarValue}
                        onValueChange={onDateChange}
                      />
                    </Popover.Content>
                  </Popover.Root>
                </Field.Field>

                <!-- Assigned To -->
                <Field.Field class="gap-1">
                  <Field.Label for="task-assignee">Assigned To</Field.Label>
                  {#if isNew}
                    <Select.Root
                      type="single"
                      value={assigneeId}
                      onValueChange={(v) => (assigneeId = v)}
                    >
                      <Select.Trigger id="task-assignee" class="w-full !h-9">
                        <span class="truncate">
                          {assigneeId
                            ? userName(assigneeId)
                            : "Select member..."}
                        </span>
                      </Select.Trigger>
                      <Select.Content class="p-1">
                        {#each assignableUsers as user (user.id)}
                          <Select.Item value={user.id} label={user.full_name}>
                            {user.full_name}
                          </Select.Item>
                        {:else}
                          <div
                            class="px-2 py-1.5 text-xs text-muted-foreground"
                          >
                            No project members. Add members first.
                          </div>
                        {/each}
                      </Select.Content>
                    </Select.Root>
                  {:else}
                    <Select.Root
                      type="single"
                      value={activeAssigneeId}
                      disabled={fieldsLocked}
                    >
                      <Select.Trigger id="task-assignee" class="w-full !h-9">
                        <span class="truncate">
                          {activeAssigneeId
                            ? userName(activeAssigneeId)
                            : "Unassigned"}
                        </span>
                      </Select.Trigger>
                      <Select.Content class="p-1">
                        {#each users as user (user.id)}
                          <Select.Item value={user.id} label={user.full_name}>
                            {user.full_name}
                          </Select.Item>
                        {:else}
                          <div
                            class="px-2 py-1.5 text-xs text-muted-foreground"
                          >
                            No assignable users.
                          </div>
                        {/each}
                      </Select.Content>
                    </Select.Root>
                  {/if}
                </Field.Field>
              </div>

              <!-- Links -->
              <Field.Field class="gap-1">
                <Field.Label for="task-link-input">Links</Field.Label>
                <div class="flex items-center gap-2">
                  <Input
                    id="task-link-input"
                    bind:value={newLinkUrl}
                    placeholder="https://..."
                    class="flex-1 h-9"
                    disabled={fieldsLocked}
                    onkeydown={(e) => {
                      if (e.key === "Enter") {
                        e.preventDefault();
                        addLink(newLinkUrl);
                      }
                    }}
                  />
                  <Button
                    variant="outline"
                    class="h-9 w-9"
                    onclick={() => addLink(newLinkUrl)}
                    disabled={fieldsLocked || !newLinkUrl.trim()}
                    aria-label="Add link"
                  >
                    <PlusIcon class="size-4" />
                  </Button>
                </div>
                {#if draft.links && draft.links.length > 0}
                  <Item.Group class="pt-2 space-y-0 gap-2">
                    {#each draft.links as link (link.id || link.url)}
                      <Item.Root variant="outline" class="h-9 px-3! py-0!">
                        {#snippet child({ props })}
                          <a
                            {...props}
                            href={link.url}
                            target="_blank"
                            rel="noopener noreferrer"
                          >
                            <Item.Media variant="icon">
                              <ExternalLinkIcon />
                            </Item.Media>
                            <Item.Content>
                              <Item.Title class="truncate font-normal"
                                >{link.url}</Item.Title
                              >
                            </Item.Content>
                            <Item.Actions>
                              <Button
                                variant="ghost"
                                size="icon-sm"
                                onclick={() => removeLink(link.id || link.url)}
                                disabled={fieldsLocked}
                                aria-label="Remove link"
                              >
                                <XIcon class="size-4" />
                              </Button>
                            </Item.Actions>
                          </a>
                        {/snippet}
                      </Item.Root>
                    {/each}
                  </Item.Group>
                {/if}
              </Field.Field>
            </Field.FieldGroup>
          {/if}
        </Tabs.Content>

        {#if !isNew}
          <!-- COMMENTS TAB -->
          <Tabs.Content value="comments" class="space-y-4 pt-3">
            <Card.Root class="p-3!">
              <Card.Content class="space-y-4 p-0!">
                {#if comments.length === 0}
                  <Empty.Root>
                    <Empty.Media variant="icon"
                      ><MessageSquareIcon /></Empty.Media
                    >
                    <Empty.Header>
                      <Empty.Title>No comments yet</Empty.Title>
                      <Empty.Description
                        >Start the conversation with the project manager.</Empty.Description
                      >
                    </Empty.Header>
                  </Empty.Root>
                {:else}
                  <ScrollAreaPrimitive.Root class="relative">
                    <ScrollAreaPrimitive.Viewport
                      class="max-h-[50vh] w-full focus-visible:ring-ring/50 size-full rounded-[inherit] transition-[color,box-shadow] outline-none focus-visible:ring-[3px] focus-visible:outline-1"
                    >
                      <Item.Group class="space-y-0 gap-2">
                        {#each comments as comment (comment.id)}
                          <Item.Root variant="outline">
                            <Item.Media>
                              <Avatar class="size-8">
                                <AvatarFallback class="text-xs"
                                  >{userInitials(
                                    comment.author_id,
                                  )}</AvatarFallback
                                >
                              </Avatar>
                            </Item.Media>
                            <Item.Content>
                              <Item.Title class="flex items-center gap-1.5">
                                {userName(comment.author_id)}
                                {#if comment.author_id === currentUser?.id}
                                  <span class="text-xs text-muted-foreground"
                                    >(you)</span
                                  >
                                {/if}
                                <span
                                  class="ml-auto text-xs font-normal text-muted-foreground"
                                >
                                  • {timeAgo(comment.created_at)}
                                </span>
                              </Item.Title>
                              {#if editingCommentId === comment.id}
                                <Textarea
                                  bind:value={editBody}
                                  class="mt-1 min-h-[60px] resize-none"
                                />
                                <div class="mt-1 flex gap-2">
                                  <Button
                                    size="sm"
                                    onclick={() => saveEditComment(comment.id)}
                                    disabled={!editBody.trim()}
                                  >
                                    Save
                                  </Button>
                                  <Button
                                    size="sm"
                                    variant="outline"
                                    onclick={cancelEditComment}>Cancel</Button
                                  >
                                </div>
                              {:else}
                                <Item.Description class="whitespace-pre-wrap"
                                  >{comment.body}</Item.Description
                                >
                              {/if}
                            </Item.Content>
                            {#if comment.author_id === currentUser?.id && editingCommentId !== comment.id}
                              <Item.Actions>
                                <DropdownMenu.DropdownMenu>
                                  <DropdownMenu.DropdownMenuTrigger>
                                    <Button
                                      variant="ghost"
                                      size="icon-sm"
                                      aria-label="Comment options"
                                    >
                                      <EllipsisIcon class="size-4" />
                                    </Button>
                                  </DropdownMenu.DropdownMenuTrigger>
                                  <DropdownMenu.DropdownMenuContent align="end">
                                    <DropdownMenu.DropdownMenuItem
                                      onclick={() =>
                                        startEditComment(
                                          comment.id,
                                          comment.body,
                                        )}
                                    >
                                      <PencilIcon class="size-4" />
                                      Edit
                                    </DropdownMenu.DropdownMenuItem>
                                    <DropdownMenu.DropdownMenuItem
                                      variant="destructive"
                                      onclick={() => deleteComment(comment.id)}
                                    >
                                      <Trash2Icon class="size-4" />
                                      Delete
                                    </DropdownMenu.DropdownMenuItem>
                                  </DropdownMenu.DropdownMenuContent>
                                </DropdownMenu.DropdownMenu>
                              </Item.Actions>
                            {/if}
                          </Item.Root>
                        {/each}
                      </Item.Group>
                    </ScrollAreaPrimitive.Viewport>
                    <ScrollAreaScrollbar orientation="vertical" />
                    <ScrollAreaPrimitive.Corner />
                  </ScrollAreaPrimitive.Root>
                {/if}

                <Separator />

                <!-- Composer -->
                <InputGroup.Root>
                  <InputGroup.Textarea
                    bind:value={commentBody}
                    placeholder="Write a comment..."
                    class="min-h-[50px]"
                  />
                  <InputGroup.Addon align="block-end">
                    <InputGroup.Button
                      variant="default"
                      size="icon-sm"
                      onclick={sendComment}
                      disabled={!commentBody.trim() || commentSending}
                      aria-label="Send comment"
                    >
                      {#if commentSending}
                        <RefreshCwIcon class="size-4 animate-spin" />
                      {:else}
                        <SendIcon class="size-4" />
                      {/if}
                    </InputGroup.Button>
                  </InputGroup.Addon>
                </InputGroup.Root>
              </Card.Content>
            </Card.Root>
          </Tabs.Content>
        {/if}
      </Tabs.Root>
    {/if}

    {#if (task || isNew) && !loading && !error && activeTab !== "comments"}
      <Dialog.Footer class="gap-2">
        {#if !isNew}
          <div class="flex-1">
            <Button
              variant="outline"
              class={cn(
                "h-9 text-destructive hover:text-destructive hover:bg-destructive/10",
                deleteConfirm && "bg-destructive/10",
              )}
              onclick={handleDelete}
            >
              <Trash2Icon class="size-4" />
              {deleteConfirm ? "Click again to confirm" : "Delete task"}
            </Button>
          </div>
        {/if}
        <div class="flex gap-2 {isNew ? 'w-full justify-end' : ''}">
          <Button variant="outline" onclick={() => (open = false)} class="h-9"
            >Cancel</Button
          >
          <Button
            onclick={handleSave}
            disabled={saving || (!isNew && fieldsLocked)}
            class="gap-1.5 h-9"
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
  </Dialog.Content>
</Dialog.Root>

<!-- Submit work dialog -->
<Dialog.Root bind:open={submitOpen}>
  <Dialog.Content class="max-w-lg">
    <Dialog.Header>
      <Dialog.Title>Submit Work</Dialog.Title>
      <Dialog.Description>
        {task?.title} — this transitions the task to
        <strong>For Review</strong>.
      </Dialog.Description>
    </Dialog.Header>
    <Field.FieldGroup>
      <Field.Field>
        <Field.Label for="external-link">External Link</Field.Label>
        <Input
          id="external-link"
          bind:value={externalLink}
          placeholder="https://drive.google.com/..."
        />
      </Field.Field>
      <Field.Field>
        <Field.Label for="submit-notes">Notes</Field.Label>
        <Textarea
          id="submit-notes"
          bind:value={notes}
          placeholder="Describe what was completed"
          class="min-h-[100px]"
        />
      </Field.Field>
    </Field.FieldGroup>
    <Dialog.Footer>
      <Button variant="outline" onclick={() => (submitOpen = false)} class="h-9"
        >Cancel</Button
      >
      <Button disabled={submitting} onclick={handleSubmit} class="gap-1.5">
        <SendIcon class="size-4" />
        {submitting ? "Submitting..." : "Submit for Review"}
      </Button>
    </Dialog.Footer>
  </Dialog.Content>
</Dialog.Root>

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
        <div class="flex gap-2">
          {#each Object.entries(decisionLabel) as [value, label] (value)}
            <Button
              variant={reviewDecision === value ? "default" : "outline"}
              size="sm"
              onclick={() => (reviewDecision = value as ApprovalDecision)}
            >
              {label}
            </Button>
          {/each}
        </div>
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
      <Button disabled={reviewing} onclick={handleReview} class="gap-1.5">
        {#if reviewDecision === "approved"}
          <CheckIcon class="size-4" />
        {:else if reviewDecision === "rejected"}
          <XIcon class="size-4" />
        {:else}
          <RefreshCwIcon class="size-4" />
        {/if}
        {reviewing ? "Submitting..." : decisionLabel[reviewDecision]}
      </Button>
    </Dialog.Footer>
  </Dialog.Content>
</Dialog.Root>
