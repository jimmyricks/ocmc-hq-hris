<script lang="ts">
  import { onMount } from "svelte";
  import { page } from "$app/state";
  import { goto } from "$app/navigation";
  import * as Field from "$lib/components/native/field/index.js";
  import { Button } from "$lib/components/native/button/index.js";
  import { Input } from "$lib/components/native/input/index.js";
  import { Switch } from "$lib/components/native/switch/index.js";
  import { apiJSON } from "$lib/api/index.js";
  import { toast } from "$lib/notifications";
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
    } catch (error) {
      console.error("Failed to load workflow:", error);
    } finally {
      loading = false;
    }
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

  {#if !isNew && workflow}
    <div class="workflow-view">
      <section class="workflow-panel">
        <h2>States</h2>
        <div class="workflow-states">
          {#each workflow.state_links as state (state.id)}
            <div class="workflow-state" class:is-initial={state.is_initial}>
              <span>{state.state_slug}</span>
              {#if state.is_initial}<small>Initial</small>{/if}
            </div>
          {:else}
            <p class="workflow-empty">No states configured.</p>
          {/each}
        </div>
      </section>

      <section class="workflow-panel">
        <h2>Transitions</h2>
        <div class="workflow-transitions">
          {#each workflow.transitions as transition (transition.id)}
            <div class="workflow-transition">
              <strong>{transition.from_state_slug}</strong>
              <span class="workflow-action">{transition.action_slug}</span>
              <strong>{transition.to_state_slug}</strong>
              {#if transition.allowed_roles.length}
                <small>{transition.allowed_roles.join(", ")}</small>
              {/if}
            </div>
          {:else}
            <p class="workflow-empty">No transitions configured.</p>
          {/each}
        </div>
      </section>
    </div>
  {/if}
</div>

<style>
  .workflow-view {
    display: grid;
    gap: 16px;
  }
  .workflow-panel {
    border: 1px solid var(--border);
    border-radius: 10px;
    background: var(--card);
    padding: 18px;
  }
  .workflow-panel h2 {
    margin: 0 0 12px;
    font-size: 14px;
    font-weight: 750;
  }
  .workflow-states {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }
  .workflow-state {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    border: 1px solid var(--border);
    border-radius: 999px;
    background: #fff;
    padding: 8px 12px;
    font-size: 12px;
    font-weight: 650;
  }
  .workflow-state.is-initial {
    border-color: #9bb5f5;
    background: #edf2ff;
    color: #2457d6;
  }
  .workflow-state small {
    color: var(--muted-foreground);
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
  }
  .workflow-transitions {
    display: grid;
    gap: 8px;
  }
  .workflow-transition {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px;
    border: 1px solid var(--border);
    border-radius: 9px;
    padding: 10px 12px;
    font-size: 12px;
  }
  .workflow-action {
    border-radius: 999px;
    background: var(--secondary);
    padding: 4px 8px;
    color: var(--secondary-foreground);
    font-size: 11px;
    font-weight: 750;
  }
  .workflow-transition small {
    color: var(--muted-foreground);
  }
  .workflow-empty {
    margin: 0;
    color: var(--muted-foreground);
    font-size: 12px;
  }
</style>
