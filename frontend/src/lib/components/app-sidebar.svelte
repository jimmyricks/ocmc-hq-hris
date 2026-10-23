<script lang="ts">
  import { page } from "$app/state";
  import logo from "$lib/assets/OCMClogo.png";
  import { useAppState } from "$lib/app-state.svelte.js";
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
  import ReceiptTextIcon from "@lucide/svelte/icons/receipt-text";
  import Settings2Icon from "@lucide/svelte/icons/settings-2";
  import XIcon from "@lucide/svelte/icons/x";

  let {
    onClose,
  }: {
    onClose?: () => void;
  } = $props();

  const workspaceItems = [
    { title: "Overview", url: "/dashboard", icon: LayoutDashboardIcon },
    { title: "Planner", url: "/planner", icon: CalendarDaysIcon },
    { title: "My tasks", url: "/tasks/my", icon: CheckSquareIcon },
    { title: "My invoices", url: "/payroll/invoices", icon: ReceiptTextIcon },
  ];
  const workflowItem = {
    title: "Workflows",
    url: "/workflow",
    icon: Settings2Icon,
  };

  const operationsItems = [
    { title: "Payroll", url: "/payroll", icon: BanknoteIcon },
    { title: "Task rates", url: "/payroll/tasks-rates", icon: ListChecksIcon },
  ];

  const peopleItems = [
    { title: "User directory", url: "/hr/directory", icon: ClipboardListIcon },
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
  ];

  const appState = useAppState();
  const workspaceContext = $derived(appState.workspaceContext);
  const user = $derived(appState.user);
  const isSystemAdmin = $derived(
    workspaceContext?.capabilities?.is_system_admin ??
      Boolean(
        user?.is_superuser ||
          user?.roles?.some((role) =>
            ["Administrator", "SystemManager"].includes(role),
          ),
      ),
  );
  const canManagePayroll = $derived(
    Boolean(workspaceContext?.capabilities?.can_manage_payroll),
  );
  const canViewHRDirectory = $derived(
    Boolean(workspaceContext?.capabilities?.can_view_hr_directory),
  );
  const visibleOperationsItems = $derived(
    canManagePayroll || isSystemAdmin ? operationsItems : [],
  );
  const visiblePeopleItems = $derived(canViewHRDirectory ? peopleItems : []);
  const visibleAdminItems = $derived(isSystemAdmin ? adminItems : []);
  const canManageWorkspace = $derived(
    Boolean(
      workspaceContext?.capabilities?.can_manage_active_workspace ||
        workspaceContext?.can_manage,
    ),
  );
  const visibleWorkspaceItems = $derived(
    canManageWorkspace || isSystemAdmin
      ? [...workspaceItems, workflowItem]
      : workspaceItems,
  );
  const activeWorkspaceLabel = $derived(
    workspaceContext?.workspaces.find(
      (workspace) => workspace.id === workspaceContext?.active_workspace_id,
    )?.name ??
      (isSystemAdmin
        ? "All companies"
        : canManagePayroll
          ? "HR workspace"
          : "Workspace"),
  );

  function isActive(url: string) {
    if (url === "/payroll/invoices")
      return page.url.pathname === "/payroll/invoices";
    if (url === "/payroll/tasks-rates") return page.url.pathname === url;
    if (url === "/payroll")
      return (
        page.url.pathname === "/payroll" ||
        (page.url.pathname.startsWith("/payroll/") &&
          !page.url.pathname.startsWith("/payroll/tasks-rates") &&
          !page.url.pathname.startsWith("/payroll/invoices"))
      );
    if (url === "/workflow") {
      return (
        page.url.pathname === url || page.url.pathname.startsWith("/workflow/")
      );
    }
    return page.url.pathname === url;
  }

  function closeAfterNavigate() {
    onClose?.();
  }
</script>

<aside
  class="flex h-dvh w-60 flex-col border-r border-base-300 bg-base-100 p-4"
  aria-label="Main navigation"
>
  <div class="flex min-h-13 shrink-0 items-center gap-3 px-2 pb-4">
    <a
      href="/dashboard"
      class="flex min-w-0 flex-1 items-center gap-2.5 text-base-content no-underline"
      onclick={closeAfterNavigate}
    >
      <span
        class="grid size-9 shrink-0 place-items-center rounded-lg border border-base-300 bg-base-100"
      >
        <img class="size-7 object-contain" src={logo} alt="" />
      </span>
      <span class="grid min-w-0 gap-0.5">
        <strong class="text-sm font-semibold tracking-tight">OCMC HQ</strong>
        <small class="truncate text-xs text-base-content/60"
          >{activeWorkspaceLabel}</small
        >
      </span>
    </a>
    <label
      for="app-nav-drawer"
      class="ml-auto grid size-8 place-items-center rounded-lg border border-base-300 bg-base-100 text-base-content hover:bg-base-200 lg:hidden"
      aria-label="Close navigation"
    >
      <XIcon size={16} aria-hidden="true" />
    </label>
  </div>

  <nav class="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto py-4">
    {#if visibleWorkspaceItems.length}
      <ul class="m-0 flex list-none flex-col gap-1 p-0">
        <li
          class="px-3 pb-1 pt-0 text-xs font-semibold uppercase tracking-wider text-base-content/60"
        >
          Workspace
        </li>
        {#each visibleWorkspaceItems as item (item.url)}
          <li class="m-0 p-0">
            <a
              class="flex min-h-9 items-center gap-2.5 rounded-md px-3 text-sm font-medium text-base-content/80 hover:bg-base-200 aria-[current=page]:bg-primary/10 aria-[current=page]:font-semibold aria-[current=page]:text-primary"
              href={item.url}
              aria-current={isActive(item.url) ? "page" : undefined}
              onclick={closeAfterNavigate}
            >
              <item.icon size={16} aria-hidden="true" />
              {item.title}
            </a>
          </li>
        {/each}
      </ul>
    {/if}

    <NavProjects {onClose} />

    {#if visibleOperationsItems.length}
      <ul class="m-0 flex list-none flex-col gap-1 p-0">
        <li
          class="px-3 pb-1 pt-0 text-xs font-semibold uppercase tracking-wider text-base-content/60"
        >
          Operations
        </li>
        {#each visibleOperationsItems as item (item.url)}
          <li class="m-0 p-0">
            <a
              class="flex min-h-9 items-center gap-2.5 rounded-md px-3 text-sm font-medium text-base-content/80 hover:bg-base-200 aria-[current=page]:bg-primary/10 aria-[current=page]:font-semibold aria-[current=page]:text-primary"
              href={item.url}
              aria-current={isActive(item.url) ? "page" : undefined}
              onclick={closeAfterNavigate}
            >
              <item.icon size={16} aria-hidden="true" />
              {item.title}
            </a>
          </li>
        {/each}
      </ul>
    {/if}

    {#if visiblePeopleItems.length}
      <ul class="m-0 flex list-none flex-col gap-1 p-0">
        <li
          class="px-3 pb-1 pt-0 text-xs font-semibold uppercase tracking-wider text-base-content/60"
        >
          People
        </li>
        {#each visiblePeopleItems as item (item.url)}
          <li class="m-0 p-0">
            <a
              class="flex min-h-9 items-center gap-2.5 rounded-md px-3 text-sm font-medium text-base-content/80 hover:bg-base-200 aria-[current=page]:bg-primary/10 aria-[current=page]:font-semibold aria-[current=page]:text-primary"
              href={item.url}
              aria-current={isActive(item.url) ? "page" : undefined}
              onclick={closeAfterNavigate}
            >
              <item.icon size={16} aria-hidden="true" />
              {item.title}
            </a>
          </li>
        {/each}
      </ul>
    {/if}

    {#if toolsItems.length}
      <ul class="m-0 flex list-none flex-col gap-1 p-0">
        <li
          class="px-3 pb-1 pt-0 text-xs font-semibold uppercase tracking-wider text-base-content/60"
        >
          Creator tools
        </li>
        {#each toolsItems as item (item.url)}
          <li class="m-0 p-0">
            <a
              class="flex min-h-9 items-center gap-2.5 rounded-md px-3 text-sm font-medium text-base-content/80 hover:bg-base-200 aria-[current=page]:bg-primary/10 aria-[current=page]:font-semibold aria-[current=page]:text-primary"
              href={item.url}
              aria-current={isActive(item.url) ? "page" : undefined}
              onclick={closeAfterNavigate}
            >
              <item.icon size={16} aria-hidden="true" />
              {item.title}
            </a>
          </li>
        {/each}
      </ul>
    {/if}

    {#if visibleAdminItems.length}
      <ul class="m-0 flex list-none flex-col gap-1 p-0">
        <li
          class="px-3 pb-1 pt-0 text-xs font-semibold uppercase tracking-wider text-base-content/60"
        >
          Administration
        </li>
        {#each visibleAdminItems as item (item.url)}
          <li class="m-0 p-0">
            <a
              class="flex min-h-9 items-center gap-2.5 rounded-md px-3 text-sm font-medium text-base-content/80 hover:bg-base-200 aria-[current=page]:bg-primary/10 aria-[current=page]:font-semibold aria-[current=page]:text-primary"
              href={item.url}
              aria-current={isActive(item.url) ? "page" : undefined}
              onclick={closeAfterNavigate}
            >
              <item.icon size={16} aria-hidden="true" />
              {item.title}
            </a>
          </li>
        {/each}
      </ul>
    {/if}
  </nav>

  <NavUser
    user={{
      name: user?.full_name || user?.username || "User",
      email: user?.email ?? "",
    }}
    {onClose}
  />
</aside>
