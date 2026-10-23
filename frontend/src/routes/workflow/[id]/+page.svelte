<script lang="ts">
  import { page } from "$app/state";
  import { goto } from "$app/navigation";
  import WorkflowGraph from "$lib/components/workflow/workflow-graph.svelte";
  import { workflowApi } from "$lib/workflow/api";
  import type {
    WorkflowCatalogAction,
    WorkflowCatalogState,
    WorkflowSavePayload,
  } from "$lib/workflow/types";
  import { workspaceApi } from "$lib/workspaces/api";
  import type { WorkspaceContext } from "$lib/workspaces/types";
  import { toast } from "$lib/notifications";
  import ArrowLeftIcon from "@lucide/svelte/icons/arrow-left";
  import PlusIcon from "@lucide/svelte/icons/plus";
  import Trash2Icon from "@lucide/svelte/icons/trash-2";

  interface EditorState {
    key: string;
    stateId: string;
    label: string;
    slug: string;
    isInitial: boolean;
    x: number;
    y: number;
  }

  interface EditorTransition {
    key: string;
    fromKey: string;
    toKey: string;
    actionId: string;
    actionText: string;
    memberAllowed: boolean;
    supervisorAllowed: boolean;
  }

  const defaultStateLabels = [
    "Draft",
    "Pending",
    "For Approval",
    "Approved",
    "Needs Revision",
    "Done",
  ];
  const defaultTransitions = [
    {
      from: "Draft",
      to: "Pending",
      action: "Start",
      member: true,
      supervisor: true,
    },
    {
      from: "Pending",
      to: "For Approval",
      action: "Submit For Review",
      member: true,
      supervisor: false,
    },
    {
      from: "For Approval",
      to: "Approved",
      action: "Approve",
      member: false,
      supervisor: true,
    },
    {
      from: "For Approval",
      to: "Needs Revision",
      action: "Request Changes",
      member: false,
      supervisor: true,
    },
    {
      from: "For Approval",
      to: "Pending",
      action: "Reject",
      member: false,
      supervisor: true,
    },
    {
      from: "Needs Revision",
      to: "For Approval",
      action: "Submit For Review",
      member: true,
      supervisor: false,
    },
    {
      from: "Approved",
      to: "Done",
      action: "Complete",
      member: false,
      supervisor: true,
    },
  ];

  let workflowId = $derived(page.params.id ?? "");
  let isNew = $derived(workflowId === "new");
  let loading = $state(true);
  let saving = $state(false);
  let workspaceContext = $state<WorkspaceContext | null>(null);
  let catalogStates = $state<WorkflowCatalogState[]>([]);
  let catalogActions = $state<WorkflowCatalogAction[]>([]);
  let editorStates = $state<EditorState[]>([]);
  let editorTransitions = $state<EditorTransition[]>([]);
  let selectedStateKey = $state<string | null>(null);
  let newStateLabel = $state("");
  let newTransition = $state({
    fromKey: "",
    toKey: "",
    actionText: "",
    memberAllowed: true,
    supervisorAllowed: false,
  });

  let formData = $state({
    name: "",
    target_entity: "task",
    is_active: true,
    is_default: false,
    workspace_id: null as string | null,
  });

  function key() {
    return crypto.randomUUID();
  }

  function normalize(value: string) {
    return value
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "_");
  }

  function findState(label: string) {
    const slug = normalize(label);
    return catalogStates.find(
      (state) =>
        state.slug === slug ||
        state.label.toLowerCase() === label.trim().toLowerCase(),
    );
  }

  function findAction(label: string) {
    const slug = normalize(label);
    return catalogActions.find(
      (action) =>
        action.slug === slug ||
        action.label.toLowerCase() === label.trim().toLowerCase(),
    );
  }

  function applyDefaultTemplate() {
    editorStates = defaultStateLabels.map((label, index) => {
      const state = findState(label);
      return {
        key: key(),
        stateId: state?.id ?? "",
        label,
        slug: state?.slug ?? normalize(label),
        isInitial: index === 0,
        x: index * 240,
        y: index % 2 ? 140 : 40,
      };
    });
    editorTransitions = defaultTransitions.map((transition) => {
      const from = editorStates.find(
        (state) => state.label === transition.from,
      )!;
      const to = editorStates.find((state) => state.label === transition.to)!;
      const action = findAction(transition.action);
      return {
        key: key(),
        fromKey: from.key,
        toKey: to.key,
        actionId: action?.id ?? "",
        actionText: transition.action,
        memberAllowed: transition.member,
        supervisorAllowed: transition.supervisor,
      };
    });
    selectedStateKey = editorStates[0]?.key ?? null;
  }

  async function loadWorkflow() {
    loading = true;
    try {
      const [states, actions, context] = await Promise.all([
        workflowApi.listStates().catch(() => [] as WorkflowCatalogState[]),
        workflowApi.listActions().catch(() => [] as WorkflowCatalogAction[]),
        workspaceApi.getContext().catch(() => null),
      ]);
      catalogStates = states;
      catalogActions = actions;
      workspaceContext = context;

      if (isNew) {
        formData = {
          name: "",
          target_entity: "task",
          is_active: true,
          is_default: false,
          workspace_id: context?.active_workspace_id ?? null,
        };
        applyDefaultTemplate();
        return;
      }

      const workflow = await workflowApi.get(workflowId);
      formData = {
        name: workflow.name,
        target_entity: workflow.target_entity,
        is_active: workflow.is_active,
        is_default: workflow.is_default,
        workspace_id: workflow.workspace_id ?? null,
      };
      editorStates = workflow.state_links.map((link, index) => ({
        key: link.id,
        stateId: link.state_id,
        label: link.state_label,
        slug: link.state_slug,
        isInitial: link.is_initial,
        x: Number(link.visual_config?.x ?? index * 240),
        y: Number(link.visual_config?.y ?? (index % 2 ? 140 : 40)),
      }));
      const keyByLinkId = new Map(
        workflow.state_links.map((link, index) => [
          link.id,
          editorStates[index].key,
        ]),
      );
      editorTransitions = workflow.transitions.map((transition) => ({
        key: transition.id,
        fromKey: keyByLinkId.get(transition.from_state_link_id) ?? "",
        toKey: keyByLinkId.get(transition.to_state_link_id) ?? "",
        actionId: transition.action_id,
        actionText: transition.action_label ?? transition.action_slug,
        memberAllowed: transition.allowed_roles.includes("workspace:member"),
        supervisorAllowed: transition.allowed_roles.includes(
          "workspace:supervisor",
        ),
      }));
      selectedStateKey = editorStates[0]?.key ?? null;
    } catch (error: any) {
      toast.error(error?.message || "Failed to load workflow");
    } finally {
      loading = false;
    }
  }

  function addState() {
    const label = newStateLabel.trim();
    if (!label) return;
    if (
      editorStates.some((state) => normalize(state.label) === normalize(label))
    ) {
      toast.error("A state with that name already exists");
      return;
    }
    const catalogState = findState(label);
    const state = {
      key: key(),
      stateId: catalogState?.id ?? "",
      label,
      slug: catalogState?.slug ?? normalize(label),
      isInitial: editorStates.length === 0,
      x: 80 + editorStates.length * 220,
      y: 220,
    };
    editorStates = [...editorStates, state];
    selectedStateKey = state.key;
    newStateLabel = "";
  }

  function removeState(stateKey: string) {
    editorStates = editorStates.filter((state) => state.key !== stateKey);
    editorTransitions = editorTransitions.filter(
      (transition) =>
        transition.fromKey !== stateKey && transition.toKey !== stateKey,
    );
    if (selectedStateKey === stateKey) selectedStateKey = null;
  }

  function setInitial(stateKey: string) {
    editorStates = editorStates.map((state) => ({
      ...state,
      isInitial: state.key === stateKey,
    }));
  }

  function addTransition(
    fromKey = newTransition.fromKey,
    toKey = newTransition.toKey,
    actionText = newTransition.actionText,
    memberAllowed = newTransition.memberAllowed,
    supervisorAllowed = newTransition.supervisorAllowed,
  ) {
    if (!fromKey || !toKey || fromKey === toKey) {
      toast.error("Choose two different states");
      return;
    }
    if (!memberAllowed && !supervisorAllowed) {
      toast.error("Select at least one workspace role for the transition");
      return;
    }
    const label = actionText.trim() || "Move";
    if (
      editorTransitions.some(
        (transition) =>
          transition.fromKey === fromKey && transition.toKey === toKey,
      )
    ) {
      toast.error("A transition already connects those states");
      return;
    }
    const action = findAction(label);
    editorTransitions = [
      ...editorTransitions,
      {
        key: key(),
        fromKey,
        toKey,
        actionId: action?.id ?? "",
        actionText: label,
        memberAllowed,
        supervisorAllowed,
      },
    ];
    newTransition = {
      fromKey: "",
      toKey: "",
      actionText: "",
      memberAllowed: true,
      supervisorAllowed: false,
    };
  }

  function removeTransition(transitionKey: string) {
    editorTransitions = editorTransitions.filter(
      (transition) => transition.key !== transitionKey,
    );
  }

  function handleCanvasConnection(fromKey: string, toKey: string) {
    addTransition(fromKey, toKey, "Move", false, true);
  }

  function handleNodePosition(stateKey: string, x: number, y: number) {
    editorStates = editorStates.map((state) =>
      state.key === stateKey ? { ...state, x, y } : state,
    );
  }

  function stateLabel(stateKey: string) {
    return (
      editorStates.find((state) => state.key === stateKey)?.label ?? "Unknown"
    );
  }

  async function resolveState(
    state: EditorState,
  ): Promise<WorkflowCatalogState> {
    const existing = findState(state.label);
    if (existing) return existing;
    const created = await workflowApi.createState(state.label);
    const catalogState = {
      color: "neutral",
      ...created,
      label: created.label ?? state.label,
    };
    catalogStates = [...catalogStates, catalogState];
    return catalogState;
  }

  async function resolveAction(label: string): Promise<WorkflowCatalogAction> {
    const existing = findAction(label);
    if (existing) return existing;
    const created = await workflowApi.createAction(label);
    const catalogAction = { ...created, label: created.label ?? label };
    catalogActions = [...catalogActions, catalogAction];
    return catalogAction;
  }

  async function save() {
    if (!formData.name.trim()) {
      toast.error("Workflow name is required");
      return;
    }
    if (!editorStates.length) {
      toast.error("Add at least one workflow state");
      return;
    }
    if (!editorStates.some((state) => state.isInitial)) {
      toast.error("Choose an initial state");
      return;
    }

    saving = true;
    try {
      const stateIds = new Map<string, string>();
      for (const state of editorStates) {
        if (!state.label.trim()) throw new Error("Every state needs a label");
        const catalogState = await resolveState(state);
        state.stateId = catalogState.id;
        state.slug = catalogState.slug;
        stateIds.set(state.key, catalogState.id);
      }

      const transitions = [];
      for (const transition of editorTransitions) {
        const fromStateId = stateIds.get(transition.fromKey);
        const toStateId = stateIds.get(transition.toKey);
        if (!fromStateId || !toStateId) {
          throw new Error(
            "Every transition must connect states in this workflow",
          );
        }
        if (!transition.memberAllowed && !transition.supervisorAllowed) {
          throw new Error("Every transition needs at least one workspace role");
        }
        const action = await resolveAction(
          transition.actionText.trim() || "Move",
        );
        transition.actionId = action.id;
        transitions.push({
          from_state_id: fromStateId,
          action_id: action.id,
          to_state_id: toStateId,
          allowed_roles: [
            ...(transition.memberAllowed ? ["workspace:member"] : []),
            ...(transition.supervisorAllowed ? ["workspace:supervisor"] : []),
          ],
        });
      }

      const payload: WorkflowSavePayload = {
        name: formData.name.trim(),
        target_entity: formData.target_entity,
        workspace_id: formData.workspace_id,
        is_active: formData.is_active,
        is_default: formData.is_default,
        state_links: editorStates.map((state, index) => ({
          state_id: stateIds.get(state.key)!,
          is_initial: state.isInitial,
          sort_order: index,
          visual_config: { x: state.x, y: state.y },
        })),
        transitions,
      };

      if (isNew) {
        const created = await workflowApi.create(payload);
        toast.success("Workflow created");
        await goto(`/workflow/${created.id}`);
      } else {
        await workflowApi.update(workflowId, payload);
        toast.success("Workflow saved");
        await loadWorkflow();
      }
    } catch (error: any) {
      toast.error(error?.message || "Failed to save workflow");
    } finally {
      saving = false;
    }
  }

  $effect(() => {
    if (workflowId) loadWorkflow();
  });
</script>

<div class="flex flex-col gap-6">
  <header class="flex flex-wrap items-center gap-3">
    <a class="btn btn-ghost btn-sm gap-1.5" href="/workflow">
      <ArrowLeftIcon class="size-4" />
      Back
    </a>
    <div class="min-w-0 flex-1">
      <h1 class="truncate text-2xl font-bold tracking-tight">
        {isNew ? "New Workflow" : formData.name || "Workflow"}
      </h1>
      <p class="mt-1 text-sm text-base-content/60">
        Shape the flow visually, then fine-tune each state change and its
        access.
      </p>
    </div>
    <button
      type="button"
      class="btn btn-primary"
      onclick={save}
      disabled={saving || loading}
    >
      {saving ? "Saving..." : isNew ? "Create workflow" : "Save workflow"}
    </button>
  </header>

  {#if loading}
    <div
      class="card flex items-center justify-center bg-base-100 py-20 shadow-sm"
    >
      <span
        class="loading loading-spinner loading-lg text-primary"
        role="status"
        aria-label="Loading"
      ></span>
    </div>
  {:else}
    <section class="card bg-base-100 shadow-sm">
      <div class="card-body grid gap-4 p-5 sm:px-6 md:grid-cols-5">
        <fieldset class="fieldset min-w-0 gap-1 md:col-span-2">
          <label class="label font-semibold" for="wf-name">Workflow name</label>
          <input
            id="wf-name"
            class="input border-base-300 w-full"
            bind:value={formData.name}
            placeholder="Task workflow"
          />
        </fieldset>
        <fieldset class="fieldset min-w-0 gap-1">
          <span class="label font-semibold">Workspace</span>
          <div class="flex h-10 items-center text-sm text-base-content/70">
            {workspaceContext?.workspaces.find(
              (workspace) => workspace.id === formData.workspace_id,
            )?.name ?? "Global"}
          </div>
        </fieldset>
        <fieldset class="fieldset min-w-0 gap-1">
          <label class="label font-semibold" for="wf-active">Active</label>
          <div class="flex h-10 items-center">
            <input
              id="wf-active"
              type="checkbox"
              class="toggle toggle-primary"
              bind:checked={formData.is_active}
            />
          </div>
        </fieldset>
        <fieldset class="fieldset min-w-0 gap-1">
          <label class="label font-semibold" for="wf-default">Default</label>
          <div class="flex h-10 items-center">
            <input
              id="wf-default"
              type="checkbox"
              class="toggle toggle-primary"
              bind:checked={formData.is_default}
            />
          </div>
        </fieldset>
      </div>
    </section>

    <section class="card overflow-hidden bg-base-100 shadow-sm">
      <div class="card-body gap-4 p-5 sm:px-6">
        <div class="flex flex-row items-start justify-between gap-3">
          <div>
            <h2 class="card-title text-base font-semibold">Workflow diagram</h2>
            <p class="mt-1 text-xs text-base-content/60">
              Drag a connector between states to add a transition. Select a node
              to highlight it in the state table.
            </p>
          </div>
          <span class="badge badge-soft badge-info"
            >{editorStates.length} states</span
          >
        </div>
        <WorkflowGraph
          states={editorStates.map((state) => ({
            key: state.key,
            label: state.label,
            isInitial: state.isInitial,
            x: state.x,
            y: state.y,
          }))}
          transitions={editorTransitions.map((transition) => ({
            key: transition.key,
            fromKey: transition.fromKey,
            toKey: transition.toKey,
            label: transition.actionText,
          }))}
          selectedKey={selectedStateKey}
          onconnect={handleCanvasConnection}
          onnodeposition={handleNodePosition}
          onnodeselect={(stateKey) => (selectedStateKey = stateKey)}
        />
      </div>
    </section>

    <section class="card overflow-hidden bg-base-100 shadow-sm">
      <div class="card-body gap-4 p-5 sm:px-6">
        <div
          class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between"
        >
          <div>
            <h2 class="card-title text-base font-semibold">Workflow states</h2>
            <p class="mt-1 text-xs text-base-content/60">
              Rename states and choose the entry point for new tasks.
            </p>
          </div>
          <div class="flex w-full gap-2 sm:w-auto">
            <input
              class="input border-base-300 w-full"
              bind:value={newStateLabel}
              placeholder="Add a state"
              list="workflow-state-options"
              aria-label="New state name"
              onkeydown={(event) => event.key === "Enter" && addState()}
            />
            <button
              type="button"
              class="btn btn-outline border-base-300"
              onclick={addState}
              aria-label="Add state"
            >
              <PlusIcon class="size-4" />
              <span class="hidden sm:inline">Add state</span>
            </button>
          </div>
          <datalist id="workflow-state-options">
            {#each catalogStates as state}
              <option value={state.label}></option>
            {/each}
          </datalist>
        </div>
      </div>
      <div class="overflow-x-auto">
        <table class="table table-zebra">
          <thead>
            <tr>
              <th class="w-14">#</th>
              <th>State name</th>
              <th>Entry state</th>
              <th>Outgoing actions</th>
              <th class="w-20 text-right">Remove</th>
            </tr>
          </thead>
          <tbody>
            {#each editorStates as state, index (state.key)}
              <tr
                class={selectedStateKey === state.key
                  ? "bg-primary/10"
                  : "cursor-pointer hover:bg-base-200"}
                onclick={() => (selectedStateKey = state.key)}
              >
                <td class="font-mono text-xs text-base-content/50">
                  {String(index + 1).padStart(2, "0")}
                </td>
                <td class="min-w-52">
                  <label class="sr-only" for={`state-${state.key}`}
                    >State name</label
                  >
                  <input
                    id={`state-${state.key}`}
                    class="input input-sm border-base-300 w-full max-w-sm"
                    bind:value={state.label}
                    aria-label={`State name for row ${index + 1}`}
                  />
                </td>
                <td>
                  <label class="flex cursor-pointer items-center gap-2">
                    <input
                      type="radio"
                      name="initial-workflow-state"
                      class="radio radio-primary radio-sm"
                      checked={state.isInitial}
                      onchange={() => setInitial(state.key)}
                      aria-label={`Set ${state.label} as initial state`}
                    />
                    {#if state.isInitial}
                      <span class="badge badge-soft badge-primary">Initial</span
                      >
                    {:else}
                      <span class="text-sm text-base-content/60"
                        >Set initial</span
                      >
                    {/if}
                  </label>
                </td>
                <td>
                  <div class="flex flex-wrap gap-1.5">
                    {#each editorTransitions.filter((transition) => transition.fromKey === state.key) as transition (transition.key)}
                      <span class="badge badge-outline">
                        {stateLabel(transition.toKey)}
                      </span>
                    {:else}
                      <span class="text-sm text-base-content/45"
                        >No next state</span
                      >
                    {/each}
                  </div>
                </td>
                <td class="text-right">
                  <button
                    type="button"
                    class="btn btn-ghost btn-sm btn-square"
                    aria-label={`Remove ${state.label}`}
                    onclick={(event) => {
                      event.stopPropagation();
                      removeState(state.key);
                    }}
                  >
                    <Trash2Icon class="size-4" />
                  </button>
                </td>
              </tr>
            {:else}
              <tr>
                <td colspan={5} class="py-10 text-center text-base-content/60">
                  Add a state to start building this workflow.
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </section>

    <section class="card overflow-hidden bg-base-100 shadow-sm">
      <div class="card-body gap-5 p-5 sm:px-6">
        <div class="flex flex-row items-start justify-between gap-3">
          <div>
            <h2 class="card-title text-base font-semibold">
              Transition matrix
            </h2>
            <p class="mt-1 text-xs text-base-content/60">
              Each row defines what can happen before a task moves to its next
              state.
            </p>
          </div>
          <span class="badge badge-outline"
            >{editorTransitions.length} transitions</span
          >
        </div>
        <div
          class="grid gap-3 rounded-2xl bg-base-200/60 p-4 lg:grid-cols-[1fr_1fr_1fr_auto] lg:items-end"
        >
          <fieldset class="fieldset min-w-0 gap-1.5">
            <label class="label font-semibold" for="new-transition-from"
              >Before</label
            >
            <select
              id="new-transition-from"
              class="select border-base-300 w-full"
              bind:value={newTransition.fromKey}
            >
              <option value="" disabled>Choose current state</option>
              {#each editorStates as state (state.key)}
                <option value={state.key}>{state.label}</option>
              {/each}
            </select>
          </fieldset>
          <fieldset class="fieldset min-w-0 gap-1.5">
            <label class="label font-semibold" for="new-transition-action"
              >Action label</label
            >
            <input
              id="new-transition-action"
              class="input border-base-300 w-full"
              bind:value={newTransition.actionText}
              placeholder="e.g. Submit for review"
              list="workflow-action-options"
            />
          </fieldset>
          <fieldset class="fieldset min-w-0 gap-1.5">
            <label class="label font-semibold" for="new-transition-to"
              >After / next state</label
            >
            <select
              id="new-transition-to"
              class="select border-base-300 w-full"
              bind:value={newTransition.toKey}
            >
              <option value="" disabled>Choose next state</option>
              {#each editorStates as state (state.key)}
                <option value={state.key}>{state.label}</option>
              {/each}
            </select>
          </fieldset>
          <button
            type="button"
            class="btn btn-primary lg:mb-0.5"
            onclick={() => addTransition()}
            disabled={editorStates.length < 2}
          >
            <PlusIcon class="size-4" />
            Add transition
          </button>
          <div class="flex flex-wrap gap-4 lg:col-span-4">
            <label class="flex cursor-pointer items-center gap-2 text-sm">
              <input
                type="checkbox"
                class="checkbox checkbox-sm checkbox-primary"
                bind:checked={newTransition.memberAllowed}
              />
              Member can move
            </label>
            <label class="flex cursor-pointer items-center gap-2 text-sm">
              <input
                type="checkbox"
                class="checkbox checkbox-sm checkbox-primary"
                bind:checked={newTransition.supervisorAllowed}
              />
              Supervisor can move
            </label>
          </div>
        </div>

        <datalist id="workflow-action-options">
          {#each catalogActions as action}
            <option value={action.label}></option>
          {/each}
        </datalist>

        <div class="overflow-x-auto">
          <table class="table table-zebra">
            <thead>
              <tr>
                <th>Before</th>
                <th>Action</th>
                <th>After / next state</th>
                <th>Who can move it?</th>
                <th class="w-16"><span class="sr-only">Remove</span></th>
              </tr>
            </thead>
            <tbody>
              {#each editorTransitions as transition (transition.key)}
                <tr>
                  <td class="min-w-44">
                    <span class="badge badge-soft badge-neutral">
                      {stateLabel(transition.fromKey)}
                    </span>
                  </td>
                  <td class="min-w-48">
                    <label class="sr-only" for={`action-${transition.key}`}
                      >Action label</label
                    >
                    <input
                      id={`action-${transition.key}`}
                      class="input input-sm border-base-300 w-full"
                      bind:value={transition.actionText}
                      placeholder="Action label"
                    />
                  </td>
                  <td class="min-w-52">
                    <select
                      class="select select-sm border-base-300 w-full"
                      bind:value={transition.toKey}
                      aria-label={`Next state after ${stateLabel(transition.fromKey)}`}
                    >
                      <option value="" disabled>Select state</option>
                      {#each editorStates as state (state.key)}
                        <option value={state.key}>{state.label}</option>
                      {/each}
                    </select>
                  </td>
                  <td class="min-w-64">
                    <div class="flex flex-wrap gap-x-4 gap-y-2">
                      <label
                        class="flex cursor-pointer items-center gap-2 text-sm"
                      >
                        <input
                          type="checkbox"
                          class="checkbox checkbox-sm checkbox-primary"
                          bind:checked={transition.memberAllowed}
                        />
                        <span
                          class={transition.memberAllowed
                            ? "badge badge-soft badge-info"
                            : "badge badge-ghost"}
                        >
                          Member
                        </span>
                      </label>
                      <label
                        class="flex cursor-pointer items-center gap-2 text-sm"
                      >
                        <input
                          type="checkbox"
                          class="checkbox checkbox-sm checkbox-primary"
                          bind:checked={transition.supervisorAllowed}
                        />
                        <span
                          class={transition.supervisorAllowed
                            ? "badge badge-soft badge-warning"
                            : "badge badge-ghost"}
                        >
                          Supervisor
                        </span>
                      </label>
                    </div>
                  </td>
                  <td class="text-right">
                    <button
                      type="button"
                      class="btn btn-ghost btn-sm btn-square"
                      aria-label={`Remove transition from ${stateLabel(transition.fromKey)} to ${stateLabel(transition.toKey)}`}
                      onclick={() => removeTransition(transition.key)}
                    >
                      <Trash2Icon class="size-4" />
                    </button>
                  </td>
                </tr>
              {:else}
                <tr>
                  <td colspan={5} class="py-12 text-center">
                    <div
                      class="mx-auto grid max-w-sm justify-items-center gap-2"
                    >
                      <span class="text-sm font-semibold"
                        >No transitions yet</span
                      >
                      <span class="text-sm text-base-content/60">
                        Connect states in the diagram or add a before/after
                        action above.
                      </span>
                    </div>
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  {/if}
</div>
