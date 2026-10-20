<script lang="ts">
  import { page } from "$app/state";
  import favicon from "$lib/assets/favicon.svg";
  import "../app.css";
  import AppSidebar from "$lib/components/app-sidebar.svelte";
  import AssistantChat from "$lib/components/assistant-chat.svelte";
  import * as Breadcrumb from "$lib/components/ui/breadcrumb/index.js";
  import { Separator } from "$lib/components/ui/separator/index.js";
  import * as Sidebar from "$lib/components/ui/sidebar/index.js";
  import { Toaster } from "$lib/components/ui/sonner";

  let { children } = $props();
  let isPublic = $derived(page.url.pathname === "/login");

  type Crumb = { label: string; href: string; isLast: boolean };

  const LABEL_OVERRIDES: Record<string, string> = {
    "model-editor": "Model Editor",
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

  function buildCrumbs(
    pathname: string,
    routeId: string | null,
    params: Record<string, string>,
  ) {
    const parts = pathname.split("/").filter(Boolean);
    const routeParts = (routeId || "").split("/").filter(Boolean);
    const out: Crumb[] = [];
    let href = "";
    for (let i = 0; i < parts.length; i++) {
      const segment = parts[i];
      href += `/${segment}`;
      const routeSegment = routeParts[i] || "";
      const match = routeSegment.match(/^\[(\w+)\]$/);
      const paramName = match ? match[1] : null;
      const label = paramName === "id" ? segment : formatSegment(segment);
      out.push({ label, href, isLast: i === parts.length - 1 });
    }
    return out.length ? out : [{ label: "Home", href: "/", isLast: true }];
  }

  const crumbs = $derived(
    buildCrumbs(page.url.pathname, page.route?.id ?? null, page.params),
  );
</script>

<svelte:head>
  <title>OCMC HQ</title>
  <link rel="icon" type="image/png" href={favicon} />
  <link rel="apple-touch-icon" href={favicon} />
</svelte:head>

{#if isPublic}
  <div class="min-h-screen bg-background text-card-foreground">
    {@render children()}
  </div>
{:else}
  <Sidebar.Provider>
    <AppSidebar />
    <Sidebar.Inset class="hq-workspace min-h-svh bg-background">
      <header
        class="sticky top-0 z-30 flex h-16 shrink-0 items-center border-b border-border/70 bg-background/90 px-4 backdrop-blur-xl md:px-8"
      >
        <div class="flex w-full items-center gap-3">
          <Sidebar.Trigger class="-ms-1 rounded-lg" />
          <Separator
            orientation="vertical"
            class="data-[orientation=vertical]:h-5"
          />
          <Breadcrumb.Root>
            <Breadcrumb.List class="text-xs sm:text-sm">
              {#each crumbs as crumb, i (crumb.href)}
                {#if i > 0}
                  <Breadcrumb.Separator class="hidden sm:block" />
                {/if}
                <Breadcrumb.Item class={crumb.isLast ? "" : "hidden sm:block"}>
                  {#if crumb.isLast}
                    <Breadcrumb.Page class="font-medium text-foreground">
                      {crumb.label}
                    </Breadcrumb.Page>
                  {:else}
                    <Breadcrumb.Link href={crumb.href}>
                      {crumb.label}
                    </Breadcrumb.Link>
                  {/if}
                </Breadcrumb.Item>
              {/each}
            </Breadcrumb.List>
          </Breadcrumb.Root>
          <div
            class="ms-auto hidden items-center gap-2 rounded-md border border-border/70 bg-card px-3 py-1.5 text-[11px] font-medium tracking-wide text-muted-foreground md:flex"
          >
            <span class="size-1.5 rounded-full bg-emerald-500"></span>
            COMPANY WORKSPACE
          </div>
        </div>
      </header>
      <main
        class="mx-auto flex w-full max-w-[1680px] flex-1 flex-col px-4 py-6 sm:px-6 lg:px-9 lg:py-8"
      >
        {@render children()}
      </main>
    </Sidebar.Inset>
  </Sidebar.Provider>
  <AssistantChat />
{/if}

<Toaster />
