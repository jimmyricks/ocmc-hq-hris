<script lang="ts">
  import { browser } from "$app/environment";
  import { get } from "svelte/store";
  import { Svelvet, Node, Anchor } from "svelvet";
  import type { Connections } from "svelvet";

  export interface WorkflowGraphState {
    key: string;
    label: string;
    isInitial: boolean;
    x: number;
    y: number;
  }

  export interface WorkflowGraphTransition {
    key: string;
    fromKey: string;
    toKey: string;
    label: string;
  }

  let {
    states,
    transitions,
    selectedKey = null,
    onconnect,
    onnodeposition,
    onnodeselect,
  }: {
    states: WorkflowGraphState[];
    transitions: WorkflowGraphTransition[];
    selectedKey?: string | null;
    onconnect?: (fromKey: string, toKey: string) => void;
    onnodeposition?: (key: string, x: number, y: number) => void;
    onnodeselect?: (key: string) => void;
  } = $props();

  function nodeKey(id: unknown): string {
    return String(id ?? "").replace(/^N-/, "");
  }

  function connectionsFor(stateKey: string): Connections {
    return transitions
      .filter((transition) => transition.fromKey === stateKey)
      .map((transition) => transition.toKey);
  }

  function handleConnection(event: CustomEvent) {
    const fromKey = nodeKey(event.detail?.node?.id);
    const toKey = nodeKey(event.detail?.connectedNode?.id);
    if (fromKey && toKey) onconnect?.(fromKey, toKey);
  }

  function handleNodeRelease(event: CustomEvent) {
    const node = event.detail?.node;
    const key = nodeKey(node?.id);
    const position = node?.position
      ? (get(node.position) as { x: number; y: number })
      : null;
    if (key && position) onnodeposition?.(key, position.x, position.y);
  }

  function handleNodeClick(event: CustomEvent) {
    const key = nodeKey(event.detail?.node?.id);
    if (key) onnodeselect?.(key);
  }
</script>

<div class="workflow-graph">
  {#if browser}
    <Svelvet
      id="workflow-editor"
      controls
      minimap
      fitView
      edgeStyle="bezier"
      endStyles={[null, "arrow"]}
      on:connection={handleConnection}
    >
      {#each states as state (state.key)}
        <Node
          id={state.key}
          position={{ x: state.x, y: state.y }}
          dimensions={{ width: 220, height: 76 }}
          editable={false}
          on:nodeReleased={handleNodeRelease}
          on:nodeClicked={handleNodeClick}
        >
          <div
            class="workflow-state-node"
            class:selected={state.key === selectedKey}
            class:initial={state.isInitial}
          >
            <div class="state-label">{state.label}</div>
            {#if state.isInitial}
              <div class="state-meta">Initial</div>
            {/if}
          </div>
          <Anchor
            slot="anchorWest"
            id={`in-${state.key}`}
            input
            direction="west"
            title="Incoming transition"
          />
          <Anchor
            slot="anchorEast"
            id={`out-${state.key}`}
            output
            direction="east"
            connections={connectionsFor(state.key)}
            edgeStyle="bezier"
            endStyles={[null, "arrow"]}
            title="Drag to connect"
            on:connection={handleConnection}
          />
        </Node>
      {/each}
    </Svelvet>
  {/if}
</div>

<style>
  .workflow-state-node {
    box-sizing: border-box;
    display: flex;
    width: 100%;
    height: 100%;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 2px;
    border: 1px solid var(--color-base-300);
    border-radius: 10px;
    background: var(--color-base-100);
    color: var(--color-base-content);
    font-weight: 600;
    box-shadow: 0 1px 3px rgb(0 0 0 / 0.08);
  }

  .workflow-state-node.selected {
    border-color: var(--color-primary);
    background: var(--color-primary);
    color: var(--color-primary-content);
  }

  .workflow-state-node.initial:not(.selected) {
    border-color: var(--color-info);
    background: color-mix(
      in srgb,
      var(--color-info) 12%,
      var(--color-base-100)
    );
  }

  .state-label {
    overflow: hidden;
    max-width: 180px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .state-meta {
    font-size: 0.7rem;
    font-weight: 500;
    opacity: 0.7;
    text-transform: uppercase;
  }

  .workflow-graph {
    height: 560px;
    min-height: 420px;
    overflow: hidden;
    border: 1px solid var(--color-base-300);
    border-radius: 12px;
    background: linear-gradient(var(--color-base-200) 1px, transparent 1px),
      linear-gradient(90deg, var(--color-base-200) 1px, transparent 1px);
    background-size: 24px 24px;
  }
</style>
