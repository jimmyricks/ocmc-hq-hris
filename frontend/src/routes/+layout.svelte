<script lang="ts">
  import { page } from "$app/state";
  import favicon from "$lib/assets/favicon.svg";
  import "../app.css";
  import AppSidebar from "$lib/components/app-sidebar.svelte";
  import AssistantChat from "$lib/components/assistant-chat.svelte";
  import Toaster from "$lib/components/design/toaster.svelte";
  import MenuIcon from "@lucide/svelte/icons/menu";

  let { children } = $props();
  let isPublic = $derived(page.url.pathname === "/login");
  let navOpen = $state(false);

  type Crumb = { label: string; href: string; isLast: boolean };

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

  function buildCrumbs(pathname: string, routeId: string | null): Crumb[] {
    const parts = pathname.split("/").filter(Boolean);
    const routeParts = (routeId || "").split("/").filter(Boolean);
    const out: Crumb[] = [];
    let href = "";
    for (let i = 0; i < parts.length; i++) {
      const segment = parts[i];
      href += `/${segment}`;
      const match = (routeParts[i] || "").match(/^\[(\w+)\]$/);
      const label = match?.[1] === "id" ? segment : formatSegment(segment);
      out.push({ label, href, isLast: i === parts.length - 1 });
    }
    return out.length ? out : [{ label: "Home", href: "/dashboard", isLast: true }];
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
  <div class="min-h-screen bg-background text-card-foreground">
    {@render children()}
  </div>
{:else}
  <div class="hq-shell">
    <button
      class="hq-mobile-scrim"
      data-open={navOpen}
      type="button"
      aria-label="Close navigation"
      tabindex={navOpen ? 0 : -1}
      onclick={() => (navOpen = false)}
    ></button>
    <AppSidebar open={navOpen} onClose={() => (navOpen = false)} />

    <div class="hq-main">
      <header class="hq-topbar">
        <button
          class="hq-mobile-menu"
          type="button"
          aria-label="Open navigation"
          aria-expanded={navOpen}
          onclick={() => (navOpen = true)}
        >
          <MenuIcon size={18} />
        </button>
        <span class="hq-topbar__divider" aria-hidden="true"></span>
        <nav class="hq-breadcrumb" aria-label="Breadcrumb">
          {#each crumbs as crumb, i (crumb.href)}
            {#if i > 0}<span class="hq-breadcrumb__separator">/</span>{/if}
            {#if crumb.isLast}
              <span aria-current="page">{crumb.label}</span>
            {:else}
              <a href={crumb.href}>{crumb.label}</a>
            {/if}
          {/each}
        </nav>
        <div class="hq-topbar__context">
          <span></span>
          Company workspace
        </div>
      </header>
      <main class="hq-page">
        {@render children()}
      </main>
    </div>
  </div>
  <AssistantChat />
{/if}

<Toaster />

<style>
  .hq-topbar__divider {
    width: 1px;
    height: 22px;
    background: #e2e7ef;
  }
  .hq-breadcrumb {
    display: flex;
    min-width: 0;
    align-items: center;
    gap: 9px;
    color: #344256;
    font-size: 12px;
  }
  .hq-breadcrumb a {
    color: #7a8798;
    text-decoration: none;
  }
  .hq-breadcrumb a:hover {
    color: #2457d6;
  }
  .hq-breadcrumb [aria-current="page"] {
    overflow: hidden;
    font-weight: 650;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .hq-breadcrumb__separator {
    color: #aab4c1;
  }
  .hq-topbar__context {
    display: flex;
    align-items: center;
    gap: 7px;
    margin-left: auto;
    color: #758196;
    font-size: 10px;
    font-weight: 650;
    letter-spacing: 0.075em;
    text-transform: uppercase;
  }
  .hq-topbar__context span {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: #27a875;
    box-shadow: 0 0 0 3px #e5f5ed;
  }
  @media (max-width: 800px) {
    .hq-topbar__context {
      display: none;
    }
  }
</style>
