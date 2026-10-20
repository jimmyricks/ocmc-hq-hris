<script lang="ts">
  import { page } from "$app/state";
  import { goto } from "$app/navigation";
  import { browser } from "$app/environment";
  import { refCache } from "$lib/task-manager/ref-cache.js";
  import type { Project, User } from "$lib/task-manager/types.js";
  import ProjectFormModal from "./project-form-modal.svelte";
  import { workspaceApi } from "$lib/workspaces/api";
  import PlusIcon from "@lucide/svelte/icons/plus";
  import LayersIcon from "@lucide/svelte/icons/layers";

  let {
    onClose,
  }: {
    onClose?: () => void;
  } = $props();

  let projects = $state<Project[]>([]);
  let users = $state<User[]>([]);
  let loading = $state(true);
  let createOpen = $state(false);
  let canManageProjects = $state(false);

  $effect(() => {
    if (!browser) return;
    loadData();
  });

  async function loadData() {
    loading = true;
    try {
      const [projectData, context] = await Promise.all([
        refCache.getProjects(),
        workspaceApi.getContext(),
      ]);
      projects = projectData;
      canManageProjects = context.can_manage;
    } catch (err) {
      console.error("Failed to load projects:", err);
      projects = [];
    } finally {
      loading = false;
    }
  }

  $effect(() => {
    if (!createOpen || users.length > 0) return;
    refCache.getUsers().then((rows) => (users = rows)).catch(() => {});
  });

  function handleCreate() {
    if (canManageProjects) createOpen = true;
  }

  function onProjectSaved(saved: Project) {
    refCache.invalidate("projects");
    const exists = projects.some((project) => project.id === saved.id);
    projects = exists
      ? projects.map((project) => (project.id === saved.id ? saved : project))
      : [...projects, saved];
    if (!exists) goto(`/project/${saved.id}`);
  }
</script>

<section class="hq-nav-group">
  <div class="hq-nav-group__heading">
    <span>Projects</span>
    {#if canManageProjects}
      <button
        class="hq-nav-add"
        type="button"
        aria-label="Add project"
        onclick={handleCreate}
      >
        <PlusIcon size={15} />
      </button>
    {/if}
  </div>
  <a
    class="hq-nav-link"
    href="/project/all"
    aria-current={page.url.pathname === "/project/all" ? "page" : undefined}
    onclick={() => onClose?.()}
  >
    <span class="hq-nav-link__icon"><LayersIcon size={17} /></span>
    All tasks
  </a>
  {#if loading}
    <div class="hq-project-placeholder"><span></span><span></span></div>
  {:else if projects.length === 0}
    <p class="hq-project-empty">No projects yet</p>
  {:else}
    {#each projects as project (project.id)}
      <a
        class="hq-nav-link"
        href="/project/{project.id}"
        aria-current={page.url.pathname === `/project/${project.id}` ? "page" : undefined}
        onclick={() => onClose?.()}
      >
        <span
          class="hq-project-dot"
          style:background-color={project.color || "#8291a5"}
        ></span>
        <span class="hq-project-name">{project.name}</span>
      </a>
    {/each}
  {/if}
</section>

<ProjectFormModal bind:open={createOpen} {users} onSaved={onProjectSaved} />

<style>
  .hq-nav-add {
    display: grid;
    width: 23px;
    height: 23px;
    place-items: center;
    border: 1px solid transparent;
    border-radius: 6px;
    background: transparent;
    color: #7a8798;
    cursor: pointer;
  }
  .hq-nav-add:hover {
    border-color: #dbe1e9;
    background: #fff;
    color: #2457d6;
  }
  .hq-project-dot {
    width: 9px;
    height: 9px;
    flex: none;
    border-radius: 3px;
  }
  .hq-project-name {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .hq-project-empty {
    margin: 2px 10px;
    color: #8792a2;
    font-size: 12px;
  }
  .hq-project-placeholder {
    display: grid;
    gap: 7px;
    padding: 7px 11px;
  }
  .hq-project-placeholder span {
    height: 9px;
    border-radius: 5px;
    background: #eef2f7;
  }
  .hq-project-placeholder span:last-child {
    width: 72%;
  }
</style>
