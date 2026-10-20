<script lang="ts">
  import { onMount } from "svelte";
  import { page } from "$app/state";
  import { goto } from "$app/navigation";
  import * as Field from "$lib/components/ui/field/index.js";
  import { Button } from "$lib/components/ui/button/index.js";
  import { Input } from "$lib/components/ui/input/index.js";
  import { Switch } from "$lib/components/ui/switch/index.js";
  import { apiJSON } from "$lib/api/index.js";
  import { toast } from "svelte-sonner";
  import { SvelteFlow, Background, Controls, MiniMap } from "@xyflow/svelte";
  import "@xyflow/svelte/dist/style.css";
  import ArrowLeftIcon from "@lucide/svelte/icons/arrow-left";

  interface Workflow {
    id: string;
    name: string;
    target_entity: string;
    is_active: boolean;
    state_links: Array<{ id: string; state_slug: string; is_initial: boolean }>;
    transitions: Array<{
      id: string;
      from_state_slug: string;
      action_slug: string;
      to_state_slug: string;
      allowed_roles: string[];
    }>;
  }

  let workflowId = $derived(page.params.id ?? "");
  let isNew = $derived(workflowId === "new");
  let workflow = $state<Workflow | null>(null);
  let loading = $state(true);
  let saving = $state(false);

  let formData = $state({
    name: "",
    target_entity: "",
    is_active: true,
  });

  let nodes = $state<any[]>([]);
  let edges = $state<any[]>([]);

  async function loadWorkflow() {
    if (isNew) {
      workflow = null;
      formData = { name: "", target_entity: "", is_active: true };
      loading = false;
      return;
    }

    loading = true;
    try {
      const data = await apiJSON(`/api/workflow/${workflowId}`);
      workflow = data.data;
      formData = {
        name: data.data?.name || "",
        target_entity: data.data?.target_entity || "",
        is_active: !!data.data?.is_active,
      };
      convertToFlow();
    } catch (error) {
      console.error("Failed to load workflow:", error);
    } finally {
      loading = false;
    }
  }

  function convertToFlow() {
    if (!workflow) return;

    nodes = workflow.state_links.map((state, index) => ({
      id: state.id,
      type: "default",
      position: {
        x: 100 + (index % 3) * 200,
        y: 100 + Math.floor(index / 3) * 150,
      },
      data: { label: state.state_slug, isInitial: state.is_initial },
    }));

    edges = workflow.transitions.map((transition) => ({
      id: transition.id,
      source: transition.from_state_slug,
      target: transition.to_state_slug,
      label: transition.action_slug,
    }));
  }

  async function save() {
    if (!formData.name || !formData.target_entity) return;
    saving = true;
    try {
      const endpoint = isNew ? "/api/workflow" : `/api/workflow/${workflowId}`;
      const method = isNew ? "POST" : "PUT";
      const data = await apiJSON(endpoint, {
        method,
        body: JSON.stringify(formData),
      });
      if (isNew && data.data?.id) {
        goto(`/workflow/${data.data.id}`);
      }
      toast.success(isNew ? "Workflow created" : "Workflow saved");
    } catch (error) {
      console.error("Failed to save workflow:", error);
      toast.error("Failed to save workflow");
    } finally {
      saving = false;
    }
  }

  onMount(() => {
    loadWorkflow();
  });

  $effect(() => {
    if (workflowId) {
      loadWorkflow();
    }
  });
</script>

<div class="flex flex-col gap-6">
  <div class="flex items-center gap-2">
    <Button variant="ghost" size="sm" href="/workflow" class="gap-1.5">
      <ArrowLeftIcon class="size-4" />
      Back
    </Button>
    <div class="flex-1">
      <h1 class="text-2xl font-bold tracking-tight">
        {isNew ? "New Workflow" : formData.name || "Workflow"}
      </h1>
    </div>
    <Button onclick={save} disabled={saving}>
      {saving ? "Saving..." : isNew ? "Create" : "Save"}
    </Button>
  </div>

  <div class="rounded-xl border p-4">
    <div class="grid grid-cols-1 gap-4 md:grid-cols-3">
      <Field.Field class="gap-1">
        <Field.Label for="wf-name">Workflow Name</Field.Label>
        <Input
          id="wf-name"
          bind:value={formData.name}
          placeholder="e.g. Asset Lifecycle"
        />
      </Field.Field>
      <Field.Field class="gap-1">
        <Field.Label for="wf-entity">Target Entity</Field.Label>
        <Input
          id="wf-entity"
          bind:value={formData.target_entity}
          placeholder="Select entity..."
          disabled={!isNew}
        />
      </Field.Field>
      <Field.Field class="gap-1">
        <Field.Label for="wf-active">Active</Field.Label>
        <div class="flex h-10 items-center">
          <Switch id="wf-active" bind:checked={formData.is_active} />
        </div>
      </Field.Field>
    </div>
  </div>

  {#if !isNew}
    <div class="rounded-xl border" style="height: 600px;">
      <SvelteFlow {nodes} {edges} fitView>
        <Background />
        <Controls />
        <MiniMap />
      </SvelteFlow>
    </div>
  {/if}
</div>
