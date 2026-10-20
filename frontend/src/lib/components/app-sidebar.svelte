<script lang="ts">
  import { page } from "$app/state";
  import { browser } from "$app/environment";
  import logo from "$lib/assets/OCMClogo.png";
  import { getToken, getUser } from "$lib/auth";
  import { workspaceApi } from "$lib/workspaces/api";
  import { setActiveWorkspaceId } from "$lib/workspaces/context";
  import type { WorkspaceContext } from "$lib/workspaces/types";
  import NavProjects from "./nav-projects.svelte";
  import NavUser from "./nav-user.svelte";

  import LayoutDashboardIcon from "@lucide/svelte/icons/layout-dashboard";
  import CalendarDaysIcon from "@lucide/svelte/icons/calendar-days";
  import CheckSquareIcon from "@lucide/svelte/icons/check-square";
  import BanknoteIcon from "@lucide/svelte/icons/banknote";
  import ListChecksIcon from "@lucide/svelte/icons/list-checks";
  import Link2Icon from "@lucide/svelte/icons/link-2";
  import QrCodeIcon from "@lucide/svelte/icons/qr-code";
  import ClipboardListIcon from "@lucide/svelte/icons/clipboard-list";
  import Settings2Icon from "@lucide/svelte/icons/settings-2";
  import XIcon from "@lucide/svelte/icons/x";

  let {
    open = false,
    onClose,
  }: {
    open?: boolean;
    onClose?: () => void;
  } = $props();

  const workspaceItems = [
    { title: "Overview", url: "/dashboard", icon: LayoutDashboardIcon },
    { title: "Planner", url: "/planner", icon: CalendarDaysIcon },
    { title: "My tasks", url: "/tasks/my", icon: CheckSquareIcon },
  ];

  const operationsItems = [
    { title: "Payroll", url: "/payroll", icon: BanknoteIcon },
    { title: "Task rates", url: "/payroll/tasks-rates", icon: ListChecksIcon },
  ];

  const toolsItems = [
    { title: "Link shortener", url: "/utils/links", icon: Link2Icon },
    { title: "QR generator", url: "/utils/qr", icon: QrCodeIcon },
  ];

  const adminItems = [
    { title: "Workspaces", url: "/admin/workspaces", icon: Settings2Icon },
    { title: "Audit & ledger", url: "/audit", icon: ClipboardListIcon },
    { title: "Admin", url: "/admin", icon: Settings2Icon },
    { title: "Permissions", url: "/admin/permissions", icon: Settings2Icon },
    { title: "Workflows", url: "/workflow", icon: Settings2Icon },
  ];

  let workspaceContext = $state<WorkspaceContext | null>(null);
  let switchingWorkspace = $state(false);
  const user = $derived(browser ? getUser() : null);
  const isAdministrator = $derived(
    Boolean(
      user?.is_superuser ||
        user?.roles?.some((role) =>
          ["Administrator", "SystemManager"].includes(role),
        ),
    ),
  );
  const canSwitchWorkspace = $derived(
    isAdministrator || (workspaceContext?.workspaces.length ?? 0) > 1,
  );
  const activeWorkspaceLabel = $derived(
    workspaceContext?.workspaces.find(
      (workspace) => workspace.id === workspaceContext?.active_workspace_id,
    )?.name ?? (isAdministrator ? "All companies" : "Workspace"),
  );

  $effect(() => {
    if (!browser || !getToken() || workspaceContext) return;
    workspaceApi
      .getContext()
      .then((context) => (workspaceContext = context))
      .catch((error) => console.error("Failed to load workspace context:", error));
  });

  async function handleWorkspaceChange(event: Event) {
    const value = (event.currentTarget as HTMLSelectElement).value;
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

  function isActive(url: string) {
    if (url === "/payroll/tasks-rates") return page.url.pathname === url;
    if (url === "/payroll") return page.url.pathname === "/payroll" ||
      (page.url.pathname.startsWith("/payroll/") &&
        !page.url.pathname.startsWith("/payroll/tasks-rates"));
    if (url === "/workflow") {
      return page.url.pathname === url || page.url.pathname.startsWith("/workflow/");
    }
    return page.url.pathname === url;
  }

  function closeAfterNavigate() {
    onClose?.();
  }
</script>

<aside class="hq-sidebar" data-open={open} aria-label="Main navigation">
  <div class="hq-sidebar__brand">
    <a href="/dashboard" class="hq-brand-link" onclick={closeAfterNavigate}>
      <span class="hq-brand-mark">
        <img src={logo} alt="" />
      </span>
      <span class="hq-brand-copy">
        <strong>OCMC HQ</strong>
        <small>{activeWorkspaceLabel}</small>
      </span>
    </a>
    <button
      class="hq-mobile-close"
      type="button"
      aria-label="Close navigation"
      onclick={() => onClose?.()}
    >
      <XIcon size={17} />
    </button>
  </div>

  {#if canSwitchWorkspace}
    <label class="hq-workspace-switch">
      <span>Company workspace</span>
      <select
        value={workspaceContext?.active_workspace_id ??
          (workspaceContext?.is_global ? "all" : "")}
        onchange={handleWorkspaceChange}
        disabled={switchingWorkspace || !workspaceContext}
        aria-label="Select company workspace"
      >
        {#if isAdministrator}
          <option value="all">All companies</option>
        {/if}
        {#each workspaceContext?.workspaces ?? [] as workspace (workspace.id)}
          <option value={workspace.id}>{workspace.name}</option>
        {/each}
      </select>
    </label>
  {/if}

  <nav class="hq-sidebar__nav">
    <div class="hq-nav-group">
      <div class="hq-nav-group__heading">Workspace</div>
      {#each workspaceItems as item (item.url)}
        <a
          class="hq-nav-link"
          href={item.url}
          aria-current={isActive(item.url) ? "page" : undefined}
          onclick={closeAfterNavigate}
        >
          <span class="hq-nav-link__icon"><item.icon size={17} /></span>
          {item.title}
        </a>
      {/each}
    </div>

    <NavProjects {onClose} />

    <div class="hq-nav-group">
      <div class="hq-nav-group__heading">Operations</div>
      {#each operationsItems as item (item.url)}
        <a
          class="hq-nav-link"
          href={item.url}
          aria-current={isActive(item.url) ? "page" : undefined}
          onclick={closeAfterNavigate}
        >
          <span class="hq-nav-link__icon"><item.icon size={17} /></span>
          {item.title}
        </a>
      {/each}
    </div>

    <div class="hq-nav-group">
      <div class="hq-nav-group__heading">Creator tools</div>
      {#each toolsItems as item (item.url)}
        <a
          class="hq-nav-link"
          href={item.url}
          aria-current={isActive(item.url) ? "page" : undefined}
          onclick={closeAfterNavigate}
        >
          <span class="hq-nav-link__icon"><item.icon size={17} /></span>
          {item.title}
        </a>
      {/each}
    </div>

    <div class="hq-nav-group">
      <div class="hq-nav-group__heading">Administration</div>
      {#each adminItems as item (item.url)}
        <a
          class="hq-nav-link"
          href={item.url}
          aria-current={isActive(item.url) ? "page" : undefined}
          onclick={closeAfterNavigate}
        >
          <span class="hq-nav-link__icon"><item.icon size={17} /></span>
          {item.title}
        </a>
      {/each}
    </div>
  </nav>

  <NavUser
    user={{
      name: user?.full_name || user?.username || "User",
      email: user?.email ?? "",
    }}
  />
</aside>

<style>
  .hq-brand-link {
    display: flex;
    min-width: 0;
    flex: 1;
    align-items: center;
    gap: 10px;
    color: inherit;
    text-decoration: none;
  }
  .hq-brand-mark {
    display: grid;
    width: 35px;
    height: 35px;
    flex: none;
    place-items: center;
    border: 1px solid #e2e8f1;
    border-radius: 9px;
    background: #fff;
  }
  .hq-brand-mark img {
    width: 27px;
    height: 27px;
    object-fit: contain;
  }
  .hq-brand-copy {
    display: grid;
    min-width: 0;
    gap: 2px;
  }
  .hq-brand-copy strong {
    font-size: 14px;
    letter-spacing: -0.02em;
  }
  .hq-brand-copy small {
    overflow: hidden;
    color: #758196;
    font-size: 10px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .hq-workspace-switch {
    display: grid;
    gap: 6px;
    margin: 2px 0 8px;
    color: #7a8798;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
  }
  .hq-workspace-switch select {
    width: 100%;
    min-height: 39px;
    border: 1px solid #dbe1e9;
    border-radius: 8px;
    background: #fff;
    padding: 0 28px 0 10px;
    color: #344256;
    font-size: 12px;
    font-weight: 600;
    letter-spacing: normal;
    text-transform: none;
  }
</style>
