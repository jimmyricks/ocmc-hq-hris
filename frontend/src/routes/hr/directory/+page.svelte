<script lang="ts">
  import { onMount } from "svelte";
  import { goto } from "$app/navigation";
  import { getToken } from "$lib/auth";
  import { Button } from "$lib/components/ui/button/index.js";
  import * as Empty from "$lib/components/ui/empty/index.js";
  import { Input } from "$lib/components/ui/input/index.js";
  import { Spinner } from "$lib/components/ui/spinner/index.js";
  import { workspaceApi } from "$lib/workspaces/api";
  import type { DirectoryUser } from "$lib/workspaces/types";
  import { useAppState } from "$lib/app-state.svelte.js";
  import Pagination from "$lib/components/pagination.svelte";
  import SearchIcon from "@lucide/svelte/icons/search";
  import UsersIcon from "@lucide/svelte/icons/users";

  const appState = useAppState();
  let users = $state<DirectoryUser[]>([]);
  let loading = $state(true);
  let allowed = $state(false);
  let search = $state("");
  let appliedSearch = $state("");
  let page = $state(appState.tablePage("hr-directory"));
  let pageSize = $state(25);
  let total = $state(0);
  let errorMessage = $state("");

  async function load(targetPage = page) {
    loading = true;
    errorMessage = "";
    try {
      const result = await workspaceApi.getHRDirectory(
        targetPage,
        pageSize,
        appliedSearch,
      );
      if (!result.users.length && result.total > 0 && targetPage > 1) {
        return load(Math.ceil(result.total / pageSize));
      }
      users = result.users;
      total = result.total;
      page = result.page ?? targetPage;
      appState.rememberTablePage("hr-directory", page);
    } catch (error) {
      errorMessage =
        error instanceof Error
          ? error.message
          : "The directory could not load.";
    } finally {
      loading = false;
    }
  }

  function setPage(targetPage: number) {
    page = targetPage;
    appState.rememberTablePage("hr-directory", targetPage);
    void load(targetPage);
  }

  async function searchDirectory() {
    appliedSearch = search.trim();
    page = 1;
    appState.rememberTablePage("hr-directory", 1);
    await load(1);
  }

  onMount(async () => {
    if (!getToken()) {
      await goto("/login");
      return;
    }
    try {
      const boot = await appState.ensureBoot();
      allowed = Boolean(
        boot?.workspace_context?.capabilities?.can_view_hr_directory,
      );
      if (!allowed) {
        await goto("/dashboard");
        return;
      }
      await load(page);
    } catch {
      await goto("/dashboard");
    }
  });
</script>

<svelte:head>
  <title>User directory · OCMC HQ</title>
  <meta
    name="description"
    content="Read-only global directory for HR and system administrators."
  />
</svelte:head>

{#if allowed}
  <div class="flex flex-col gap-6">
    <header class="flex flex-col">
      <p
        class="text-xs font-semibold uppercase tracking-[0.14em] text-base-content/60"
      >
        People
      </p>
      <h1 class="mt-2 text-2xl font-bold tracking-tight">User directory</h1>
      <p class="mt-1 max-w-2xl text-sm text-base-content/60">
        Read-only employee directory for payroll and coordination. Account
        settings and access are managed by system administrators.
      </p>
    </header>

    <form
      class="flex flex-col gap-2 sm:flex-row"
      onsubmit={(event) => {
        event.preventDefault();
        searchDirectory();
      }}
    >
      <Input
        bind:value={search}
        placeholder="Search name, username, or email"
        aria-label="Search user directory"
        class="sm:max-w-md"
      />
      <Button type="submit" variant="primary" disabled={loading}>
        <SearchIcon data-icon="inline-start" />
        Search
      </Button>
    </form>

    {#if errorMessage}
      <p
        class="rounded-lg border border-error/20 bg-error/5 px-4 py-3 text-sm text-error"
        role="alert"
      >
        {errorMessage}
      </p>
    {/if}

    <section
      class="overflow-hidden rounded-box border border-base-300 bg-base-100"
    >
      {#if loading}
        <div class="flex min-h-48 items-center justify-center">
          <Spinner class="size-7" />
        </div>
      {:else if users.length}
        <div class="overflow-x-auto">
          <table class="table table-zebra">
            <thead>
              <tr>
                <th>Name</th>
                <th>Username</th>
                <th>Email</th>
              </tr>
            </thead>
            <tbody>
              {#each users as user (user.id)}
                <tr>
                  <td class="font-medium">{user.full_name}</td>
                  <td class="font-mono text-xs text-base-content/65">
                    {user.username}
                  </td>
                  <td>{user.email}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
        <Pagination
          {page}
          {pageSize}
          {total}
          {loading}
          pageSizeOptions={[10, 25, 50, 100]}
          onchange={setPage}
          onpagesizechange={(size) => {
            pageSize = size;
            setPage(1);
          }}
        />
      {:else}
        <Empty.Root class="py-16">
          <Empty.Media variant="icon">
            <UsersIcon />
          </Empty.Media>
          <Empty.Header>
            <Empty.Title>No directory matches</Empty.Title>
            <Empty.Description>
              Try another search term or clear the filter.
            </Empty.Description>
          </Empty.Header>
        </Empty.Root>
      {/if}
    </section>
  </div>
{/if}
