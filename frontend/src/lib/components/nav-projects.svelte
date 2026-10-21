<script lang="ts">
  import { page } from "$app/state";
  import { goto } from "$app/navigation";
  import { browser } from "$app/environment";
  import { refCache } from "$lib/task-manager/ref-cache.js";
  import type { Project, User } from "$lib/task-manager/types.js";
  import ProjectFormModal from "./project-form-modal.svelte";
  import { Button } from "$lib/components/ui/button/index.js";
  import { Skeleton } from "$lib/components/ui/skeleton/index.js";
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
    refCache
      .getUsers()
      .then((rows) => (users = rows))
      .catch(() => {});
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

<section class="flex flex-col gap-1">
  <div
    class="flex min-h-7 items-center px-3 text-xs font-semibold uppercase tracking-wider text-base-content/60"
  >
    <span>Projects</span>
    {#if canManageProjects}
      <Button
        variant="ghost"
        size="sm" icon
        class="ml-auto size-7 min-h-7"
        aria-label="Add project"
        onclick={handleCreate}
      >
        <PlusIcon size={16} aria-hidden="true" />
      </Button>
    {/if}
  </div>
  <a
    class="flex min-h-9 items-center gap-2.5 rounded-md px-3 text-sm font-medium text-base-content/80 hover:bg-base-200 aria-[current=page]:bg-primary/10 aria-[current=page]:font-semibold aria-[current=page]:text-primary"
    href="/project/all"
    aria-current={page.url.pathname === "/project/all" ? "page" : undefined}
    onclick={() => onClose?.()}
  >
    <LayersIcon size={16} aria-hidden="true" />
    All tasks
  </a>
  {#if loading}
    <div class="grid gap-2 px-3 py-2" aria-label="Loading projects">
      <Skeleton class="h-2.5 w-4/5" />
      <Skeleton class="h-2.5 w-3/5" />
    </div>
  {:else if projects.length === 0}
    <p class="m-0 px-3 py-1 text-xs text-base-content/60">No projects yet</p>
  {:else}
    {#each projects as project (project.id)}
      <a
        class="flex min-h-9 items-center gap-2.5 rounded-md px-3 text-sm font-medium text-base-content/80 hover:bg-base-200 aria-[current=page]:bg-primary/10 aria-[current=page]:font-semibold aria-[current=page]:text-primary"
        href="/project/{project.id}"
        aria-current={page.url.pathname === `/project/${project.id}`
          ? "page"
          : undefined}
        onclick={() => onClose?.()}
      >
        <span
          class="size-2 shrink-0 rounded-sm"
          style:background-color={project.color || "var(--color-base-content)"}
        ></span>
        <span class="truncate">{project.name}</span>
      </a>
    {/each}
  {/if}
</section>

<ProjectFormModal bind:open={createOpen} {users} onSaved={onProjectSaved} />
