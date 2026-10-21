<script lang="ts">
  import { page } from "$app/state";
  import { browser } from "$app/environment";
  import favicon from "$lib/assets/favicon.svg";
  import "../app.css";
  import { getToken, getUser } from "$lib/auth";
  import { workspaceApi } from "$lib/workspaces/api";
  import { theme, toggleTheme } from "$lib/theme";
  import { setActiveWorkspaceId } from "$lib/workspaces/context";
  import type { WorkspaceContext } from "$lib/workspaces/types";
  import AppSidebar from "$lib/components/app-sidebar.svelte";
  import AssistantChat from "$lib/components/assistant-chat.svelte";
  import Breadcrumbs from "$lib/components/breadcrumbs.svelte";
  import Toaster from "$lib/components/toaster.svelte";
  import { Button } from "$lib/components/ui/button/index.js";
  import * as Select from "$lib/components/ui/select/index.js";
  import MenuIcon from "@lucide/svelte/icons/menu";
  import MoonIcon from "@lucide/svelte/icons/moon";
  import SunIcon from "@lucide/svelte/icons/sun";

  let { children } = $props();
  let isPublic = $derived(page.url.pathname === "/login");
  let navOpen = $state(false);

  let workspaceContext = $state<WorkspaceContext | null>(null);
  let switchingWorkspace = $state(false);
  const user = $derived(browser ? getUser() : null);
  const isSystemAdmin = $derived(
    workspaceContext?.capabilities?.is_system_admin ??
      Boolean(
        user?.is_superuser ||
          user?.roles?.some((role) =>
            ["Administrator", "SystemManager"].includes(role),
          ),
      ),
  );
  const canSwitchWorkspace = $derived(
    isSystemAdmin ||
      (!workspaceContext?.is_global &&
        (workspaceContext?.workspaces.length ?? 0) > 1),
  );
  const activeWorkspaceLabel = $derived(
    workspaceContext?.workspaces.find(
      (workspace) => workspace.id === workspaceContext?.active_workspace_id,
    )?.name ??
      (isSystemAdmin
        ? "All companies"
        : workspaceContext?.capabilities?.can_manage_payroll
          ? "HR workspace"
          : "Workspace"),
  );

  $effect(() => {
    if (!browser || !getToken() || workspaceContext || isPublic) return;
    workspaceApi
      .getContext()
      .then((context) => (workspaceContext = context))
      .catch((error) =>
        console.error("Failed to load workspace context:", error),
      );
  });

  async function handleWorkspaceChange(value: string) {
    if (!value || switchingWorkspace) return;
    const workspaceId = value === "all" ? null : value;
    switchingWorkspace = true;
    try {
      await workspaceApi.select(workspaceId);
      setActiveWorkspaceId(workspaceId);
      window.location.reload();
    } catch (error) {
      console.error("Failed to switch workspace:", error);
    } finally {
      switchingWorkspace = false;
    }
  }

  const LABEL_OVERRIDES: Record<string, string> = {
    "tasks-rates": "Tasks & Rates",
    "task-type": "Task Types",
    "oc-audit-log": "Audit Logs",
    "task-assignment": "Task Assignments",
    "task-submission": "Task Submissions",
    "task-approval": "Task Approvals",
  };

  function formatSegment(segment: string) {
    return (
      LABEL_OVERRIDES[segment] ||
      segment
        .replace(/-/g, " ")
        .replace(/_/g, " ")
        .replace(/\b\w/g, (c) => c.toUpperCase())
    );
  }

  function buildCrumbs(pathname: string, routeId: string | null) {
    const parts = pathname.split("/").filter(Boolean);
    const routeParts = (routeId || "").split("/").filter(Boolean);
    const out: { label: string; href: string }[] = [];
    let href = "";
    for (let i = 0; i < parts.length; i++) {
      const segment = parts[i];
      href += `/${segment}`;
      const match = (routeParts[i] || "").match(/^\[(\w+)\]$/);
      const label = match?.[1] === "id" ? segment : formatSegment(segment);
      out.push({ label, href });
    }
    return out.length ? out : [{ label: "Home", href: "/dashboard" }];
  }

  const crumbs = $derived(
    buildCrumbs(page.url.pathname, page.route?.id ?? null),
  );
</script>

<svelte:head>
  <title>OCMC HQ</title>
  <link rel="icon" type="image/png" href={favicon} />
  <link rel="apple-touch-icon" href={favicon} />
</svelte:head>

{#if isPublic}
  <div class="min-h-screen bg-base-200 text-base-content">
    {@render children()}
  </div>
{:else}
  <div class="drawer min-h-screen lg:drawer-open">
    <input
      id="app-nav-drawer"
      type="checkbox"
      class="drawer-toggle"
      bind:checked={navOpen}
    />
    <div class="drawer-content min-h-screen">
      <header
        class="sticky top-0 z-20 flex min-h-14 items-center gap-3 border-b border-base-300 bg-base-100/90 px-4 backdrop-blur sm:px-6"
      >
        <Button
          variant="ghost"
          size="sm"
          icon
          class="drawer-button lg:hidden"
          aria-label="Open navigation"
          onclick={() => (navOpen = !navOpen)}
        >
          <MenuIcon size={16} aria-hidden="true" />
        </Button>
        <Breadcrumbs items={crumbs} class="text-sm" />
        <div class="ml-auto flex items-center gap-2">
          <div class="hidden items-center gap-2 sm:flex">
            {#if canSwitchWorkspace}
              <Select.Root
                type="single"
                value={workspaceContext?.active_workspace_id ??
                  (workspaceContext?.is_global ? "all" : "")}
                onValueChange={handleWorkspaceChange}
                disabled={switchingWorkspace || !workspaceContext}
                class="w-64"
              >
                <Select.Trigger
                  size="md"
                  class="w-full font-medium"
                  aria-label="Select company workspace"
                >
                  {workspaceContext?.active_workspace_id
                    ? (workspaceContext.workspaces.find(
                        (workspace) =>
                          workspace.id ===
                          workspaceContext?.active_workspace_id,
                      )?.name ?? "Select workspace")
                    : workspaceContext?.is_global
                      ? "All companies"
                      : "Select workspace"}
                </Select.Trigger>
                <Select.Content>
                  {#if isSystemAdmin}
                    <Select.Item value="all" label="All companies">
                      All companies
                    </Select.Item>
                  {/if}
                  {#each workspaceContext?.workspaces ?? [] as workspace (workspace.id)}
                    <Select.Item value={workspace.id} label={workspace.name}>
                      {workspace.name}
                    </Select.Item>
                  {/each}
                </Select.Content>
              </Select.Root>
            {:else}
              <span
                class="flex items-center gap-2 text-xs font-medium uppercase tracking-wider text-base-content/60"
              >
                <span class="size-2 rounded-full bg-success" aria-hidden="true"
                ></span>
                {activeWorkspaceLabel}
              </span>
            {/if}
          </div>
          <Button
            variant="ghost"
            icon
            aria-label={$theme === "hq-dark"
              ? "Switch to light theme"
              : "Switch to dark theme"}
            aria-pressed={$theme === "hq-dark"}
            title={$theme === "hq-dark"
              ? "Switch to light theme"
              : "Switch to dark theme"}
            onclick={toggleTheme}
          >
            {#if $theme === "hq-dark"}
              <SunIcon size={16} aria-hidden="true" />
            {:else}
              <MoonIcon size={16} aria-hidden="true" />
            {/if}
          </Button>
        </div>
      </header>
      <main class="mx-auto w-full max-w-[1440px] px-4 py-5 sm:px-6 sm:py-6">
        {@render children()}
      </main>
    </div>
    <div class="drawer-side z-40">
      <label
        for="app-nav-drawer"
        aria-label="Close navigation"
        class="drawer-overlay"
      ></label>
      <AppSidebar onClose={() => (navOpen = false)} />
    </div>
  </div>
  <AssistantChat />
{/if}

<Toaster />
