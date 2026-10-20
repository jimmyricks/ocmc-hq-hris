<script lang="ts" module>
  import BanknoteIcon from "@lucide/svelte/icons/banknote";
  import CalendarDaysIcon from "@lucide/svelte/icons/calendar-days";
  import CheckSquareIcon from "@lucide/svelte/icons/check-square";
  import ClipboardListIcon from "@lucide/svelte/icons/clipboard-list";
  import LayoutDashboardIcon from "@lucide/svelte/icons/layout-dashboard";
  import Link2Icon from "@lucide/svelte/icons/link-2";
  import ListChecksIcon from "@lucide/svelte/icons/list-checks";
  import QrCodeIcon from "@lucide/svelte/icons/qr-code";
  import Settings2Icon from "@lucide/svelte/icons/settings-2";
</script>

<script lang="ts">
  import { page } from "$app/state";
  import { browser } from "$app/environment";
  import NavProjects from "./nav-projects.svelte";
  import NavUser from "./nav-user.svelte";
  import * as Sidebar from "$lib/components/ui/sidebar/index.js";
  import * as Select from "$lib/components/ui/select/index.js";
  import logo from "$lib/assets/OCMClogo.png";
  import { getToken, getUser } from "$lib/auth";
  import { workspaceApi } from "$lib/workspaces/api";
  import { setActiveWorkspaceId } from "$lib/workspaces/context";
  import type { WorkspaceContext } from "$lib/workspaces/types";
  import type { ComponentProps } from "svelte";

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
    { title: "Model editor", url: "/model-editor", icon: Settings2Icon },
  ];

  let {
    ref = $bindable(null),
    ...restProps
  }: ComponentProps<typeof Sidebar.Root> = $props();

  let workspaceContext = $state<WorkspaceContext | null>(null);
  let switchingWorkspace = $state(false);
  const isAdministrator = $derived.by(() => {
    const user = browser ? getUser() : null;
    return Boolean(
      user?.is_superuser ||
        user?.roles?.some((role) =>
          ["Administrator", "SystemManager"].includes(role),
        ),
    );
  });
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
      .catch((error) =>
        console.error("Failed to load workspace context:", error),
      );
  });

  async function handleWorkspaceChange(value: string | undefined) {
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

  // Real logged-in user; fall back to a neutral placeholder.
  let sidebarUser = $derived(
    browser
      ? (() => {
          const u = getUser();
          return u
            ? {
                name: u.full_name || u.username || "User",
                email: u.email,
                avatar: undefined,
              }
            : { name: "Guest", email: "", avatar: undefined };
        })()
      : { name: "User", email: "", avatar: undefined },
  );

  function isActive(url: string) {
    if (url === "/payroll/tasks-rates") {
      return page.url.pathname === url;
    }
    if (url === "/payroll") {
      return (
        page.url.pathname === url ||
        (page.url.pathname.startsWith("/payroll/") &&
          !page.url.pathname.startsWith("/payroll/tasks-rates"))
      );
    }
    if (url === "/workflow") {
      return (
        page.url.pathname === url || page.url.pathname.startsWith("/workflow/")
      );
    }
    if (url === "/model-editor") {
      return (
        page.url.pathname === url ||
        page.url.pathname.startsWith("/model-editor/")
      );
    }
    return page.url.pathname === url;
  }
</script>

<Sidebar.Root bind:ref variant="inset" {...restProps} class="hq-sidebar">
  <Sidebar.Header>
    <Sidebar.Menu>
      <Sidebar.MenuItem>
        <Sidebar.MenuButton size="lg">
          {#snippet child({ props })}
            <a href="/dashboard" {...props}>
              <div
                class="flex aspect-square size-9 items-center justify-center rounded-lg bg-card"
              >
                <img src={logo} alt="OCMC Logo" class="size-7 object-contain" />
              </div>
              <div class="grid flex-1 text-start text-sm leading-tight">
                <span class="truncate font-semibold tracking-tight"
                  >OCMC HQ</span
                >
                <span class="truncate text-[11px] text-sidebar-foreground/55"
                  >{activeWorkspaceLabel}</span
                >
              </div>
            </a>
          {/snippet}
        </Sidebar.MenuButton>
      </Sidebar.MenuItem>
    </Sidebar.Menu>
  </Sidebar.Header>
  <Sidebar.Content>
    {#if canSwitchWorkspace}
      <Sidebar.Group>
        <Sidebar.GroupLabel>Company workspace</Sidebar.GroupLabel>
        <Sidebar.Menu>
          <Sidebar.MenuItem>
            <Select.Root
              type="single"
              value={workspaceContext?.active_workspace_id ??
                (workspaceContext?.is_global ? "all" : "")}
              onValueChange={handleWorkspaceChange}
            >
              <Select.Trigger
                class="h-9 w-full border-sidebar-border bg-sidebar text-xs"
                disabled={switchingWorkspace || !workspaceContext}
              >
                <span class="truncate">{activeWorkspaceLabel}</span>
              </Select.Trigger>
              <Select.Content>
                <Select.Group>
                  {#if isAdministrator}
                    <Select.Item value="all" label="All companies">
                      All companies
                    </Select.Item>
                  {/if}
                  {#each workspaceContext?.workspaces ?? [] as workspace (workspace.id)}
                    <Select.Item value={workspace.id} label={workspace.name}>
                      <span class="flex items-center gap-2">
                        <span
                          class="size-2 rounded-full"
                          style:background-color={workspace.color}
                        ></span>
                        {workspace.name}
                      </span>
                    </Select.Item>
                  {/each}
                </Select.Group>
              </Select.Content>
            </Select.Root>
          </Sidebar.MenuItem>
        </Sidebar.Menu>
      </Sidebar.Group>
    {/if}
    <Sidebar.Group>
      <Sidebar.GroupLabel>Workspace</Sidebar.GroupLabel>
      <Sidebar.Menu>
        {#each workspaceItems as item (item.url)}
          <Sidebar.MenuItem>
            <Sidebar.MenuButton
              isActive={isActive(item.url)}
              tooltipContent={item.title}
            >
              {#snippet child({ props })}
                <a href={item.url} {...props}>
                  <item.icon class="size-4" />
                  <span>{item.title}</span>
                </a>
              {/snippet}
            </Sidebar.MenuButton>
          </Sidebar.MenuItem>
        {/each}
      </Sidebar.Menu>
    </Sidebar.Group>
    <NavProjects />
    <Sidebar.Group>
      <Sidebar.GroupLabel>Operations</Sidebar.GroupLabel>
      <Sidebar.Menu>
        {#each operationsItems as item (item.url)}
          <Sidebar.MenuItem>
            <Sidebar.MenuButton
              isActive={isActive(item.url)}
              tooltipContent={item.title}
            >
              {#snippet child({ props })}
                <a href={item.url} {...props}>
                  <item.icon class="size-4" />
                  <span>{item.title}</span>
                </a>
              {/snippet}
            </Sidebar.MenuButton>
          </Sidebar.MenuItem>
        {/each}
      </Sidebar.Menu>
    </Sidebar.Group>
    <Sidebar.Group>
      <Sidebar.GroupLabel>Creator tools</Sidebar.GroupLabel>
      <Sidebar.Menu>
        {#each toolsItems as item (item.url)}
          <Sidebar.MenuItem>
            <Sidebar.MenuButton
              isActive={isActive(item.url)}
              tooltipContent={item.title}
            >
              {#snippet child({ props })}
                <a href={item.url} {...props}>
                  <item.icon class="size-4" />
                  <span>{item.title}</span>
                </a>
              {/snippet}
            </Sidebar.MenuButton>
          </Sidebar.MenuItem>
        {/each}
      </Sidebar.Menu>
    </Sidebar.Group>
    <Sidebar.Group class="mt-auto">
      <Sidebar.GroupLabel>Administration</Sidebar.GroupLabel>
      <Sidebar.Menu>
        {#each adminItems as item (item.url)}
          <Sidebar.MenuItem>
            <Sidebar.MenuButton
              isActive={isActive(item.url)}
              tooltipContent={item.title}
            >
              {#snippet child({ props })}
                <a href={item.url} {...props}>
                  <item.icon class="size-4" />
                  <span>{item.title}</span>
                </a>
              {/snippet}
            </Sidebar.MenuButton>
          </Sidebar.MenuItem>
        {/each}
      </Sidebar.Menu>
    </Sidebar.Group>
  </Sidebar.Content>
  <Sidebar.Footer>
    <NavUser user={sidebarUser} />
  </Sidebar.Footer>
</Sidebar.Root>
