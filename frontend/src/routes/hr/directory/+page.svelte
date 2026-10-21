<script lang="ts">
  import { onMount } from "svelte";
  import { goto } from "$app/navigation";
  import { getToken } from "$lib/auth";
  import { Button } from "$lib/components/ui/button/index.js";
  import * as Empty from "$lib/components/ui/empty/index.js";
  import { Input } from "$lib/components/ui/input/index.js";
  import { Spinner } from "$lib/components/ui/spinner/index.js";
  import * as Table from "$lib/components/ui/table/index.js";
  import { workspaceApi } from "$lib/workspaces/api";
  import type { DirectoryUser } from "$lib/workspaces/types";
  import SearchIcon from "@lucide/svelte/icons/search";
  import UsersIcon from "@lucide/svelte/icons/users";

  const pageSize = 50;
  let users = $state<DirectoryUser[]>([]);
  let loading = $state(true);
  let allowed = $state(false);
  let search = $state("");
  let appliedSearch = $state("");
  let page = $state(1);
  let total = $state(0);
  let errorMessage = $state("");

  const pageCount = $derived(Math.max(1, Math.ceil(total / pageSize)));

  async function load() {
    loading = true;
    errorMessage = "";
    try {
      const result = await workspaceApi.getHRDirectory(
        page,
        pageSize,
        appliedSearch,
      );
      users = result.users;
      total = result.total;
    } catch (error) {
      errorMessage =
        error instanceof Error ? error.message : "The directory could not load.";
    } finally {
      loading = false;
    }
  }

  async function searchDirectory() {
    appliedSearch = search.trim();
    page = 1;
    await load();
  }

  onMount(async () => {
    if (!getToken()) {
      await goto("/login");
      return;
    }
    try {
      const context = await workspaceApi.getContext();
      allowed = Boolean(context.capabilities?.can_view_hr_directory);
      if (!allowed) {
        await goto("/dashboard");
        return;
      }
      await load();
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
    <header class="flex flex-col gap-2">
      <p class="text-xs font-semibold uppercase tracking-[0.16em] text-primary">
        People
      </p>
      <h1 class="text-3xl font-semibold tracking-tight">User directory</h1>
      <p class="max-w-2xl text-sm text-base-content/60">
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

    <section class="overflow-hidden rounded-xl border border-base-300 bg-base-100">
      {#if loading}
        <div class="flex min-h-48 items-center justify-center">
          <Spinner class="size-7" />
        </div>
      {:else if users.length}
        <div class="overflow-x-auto">
          <Table.Root>
            <Table.Header>
              <Table.Row>
                <Table.Head>Name</Table.Head>
                <Table.Head>Username</Table.Head>
                <Table.Head>Email</Table.Head>
              </Table.Row>
            </Table.Header>
            <Table.Body>
              {#each users as user (user.id)}
                <Table.Row>
                  <Table.Cell class="font-medium">{user.full_name}</Table.Cell>
                  <Table.Cell class="font-mono text-xs text-base-content/65">
                    {user.username}
                  </Table.Cell>
                  <Table.Cell>{user.email}</Table.Cell>
                </Table.Row>
              {/each}
            </Table.Body>
          </Table.Root>
        </div>
        <footer
          class="flex flex-col gap-3 border-t border-base-300 px-4 py-3 sm:flex-row sm:items-center sm:justify-between"
        >
          <p class="text-xs text-base-content/60">
            {total} active {total === 1 ? "employee" : "employees"}
          </p>
          <div class="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page <= 1 || loading}
              onclick={() => {
                page -= 1;
                load();
              }}
            >
              Previous
            </Button>
            <span class="min-w-20 text-center text-xs text-base-content/60">
              Page {page} of {pageCount}
            </span>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= pageCount || loading}
              onclick={() => {
                page += 1;
                load();
              }}
            >
              Next
            </Button>
          </div>
        </footer>
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
