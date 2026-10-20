<script lang="ts">
  import { page } from "$app/state";
  import * as Sidebar from "$lib/components/ui/sidebar/index.js";
  import LayersIcon from "@lucide/svelte/icons/layers";
  import PlusIcon from "@lucide/svelte/icons/plus";
  import { goto } from "$app/navigation";
  import { browser } from "$app/environment";
  import { refCache } from "$lib/task-manager/ref-cache.js";
  import type { Project, User } from "$lib/task-manager/types.js";
  import ProjectFormModal from "./project-form-modal.svelte";
  import { workspaceApi } from "$lib/workspaces/api";

  let projects = $state<Project[]>([]);
  let users = $state<User[]>([]);
  let loading = $state(true);
  let createOpen = $state(false);
  let canManageProjects = $state(false);

  // Only load projects for the sidebar — not all tasks or all users.
  // Users are fetched lazily when the create-project modal opens.
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

  // Lazy-load users only when the create modal opens.
  $effect(() => {
    if (!createOpen || users.length > 0) return;
    refCache
      .getUsers()
      .then((u) => (users = u))
      .catch(() => {});
  });

  function isActive(url: string) {
    return page.url.pathname === url;
  }

  function handleCreate() {
    if (!canManageProjects) return;
    createOpen = true;
  }

  function onProjectSaved(saved: Project) {
    refCache.invalidate("projects");
    const exists = projects.some((p) => p.id === saved.id);
    projects = exists
      ? projects.map((p) => (p.id === saved.id ? saved : p))
      : [...projects, saved];
    if (!exists) {
      goto(`/project/${saved.id}`);
    }
  }
</script>

<Sidebar.Group class="group-data-[collapsible=icon]:hidden">
  <Sidebar.GroupLabel>Projects</Sidebar.GroupLabel>
  {#if canManageProjects}
    <Sidebar.GroupAction onclick={handleCreate} aria-label="Add project">
      <PlusIcon class="size-4" />
    </Sidebar.GroupAction>
  {/if}
  <Sidebar.Menu>
    {#if loading}
      <Sidebar.MenuItem>
        <Sidebar.MenuSkeleton showIcon />
      </Sidebar.MenuItem>
    {:else}
      <Sidebar.MenuItem>
        <Sidebar.MenuButton isActive={isActive("/project/all")}>
          {#snippet child({ props })}
            <a href="/project/all" {...props}>
              <LayersIcon class="size-4" />
              <span>All Tasks</span>
            </a>
          {/snippet}
        </Sidebar.MenuButton>
      </Sidebar.MenuItem>
      {#each projects as project (project.id)}
        <Sidebar.MenuItem>
          <Sidebar.MenuButton isActive={isActive(`/project/${project.id}`)}>
            {#snippet child({ props })}
              <a href="/project/{project.id}" {...props}>
                <span
                  class="size-2.5 rounded-full"
                  style="background-color: {project.color}"
                ></span>
                <span>{project.name}</span>
              </a>
            {/snippet}
          </Sidebar.MenuButton>
        </Sidebar.MenuItem>
      {:else}
        <Sidebar.MenuItem>
          <span class="px-2 text-xs text-muted-foreground">No projects</span>
        </Sidebar.MenuItem>
      {/each}
    {/if}
  </Sidebar.Menu>
</Sidebar.Group>

<ProjectFormModal bind:open={createOpen} {users} onSaved={onProjectSaved} />
