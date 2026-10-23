<script lang="ts">
  import { onMount } from "svelte";
  import { dev } from "$app/environment";
  import { env } from "$env/dynamic/public";
  import { getToken } from "$lib/auth";
  import { useAppState } from "$lib/app-state.svelte.js";
  import { Button } from "$lib/components/ui/button/index.js";
  import * as Card from "$lib/components/ui/card/index.js";
  import LoginForm from "$lib/components/login-form.svelte";
  import WorkspaceLoadingScreen from "$lib/components/workspace-loading-screen.svelte";

  type QuickLoginAccount = {
    label: string;
    username: string;
    password: string;
  };

  type QuickLoginGroup = {
    label: string;
    accounts: QuickLoginAccount[];
  };

  const personaPassword = env.PUBLIC_DEV_QUICK_LOGIN_PASSWORD ?? "";
  const personaWorkspaces = [
    {
      label: "One Heart Creative Studios",
      key: "oneheart",
      supervisor: "Roxanne",
      employees: ["Iven", "Earl"],
    },
    {
      label: "4th Street Recording Studio",
      key: "fourthstreet",
      supervisor: "Jen",
      employees: ["Jim", "Employee 2"],
    },
    {
      label: "OC Music School",
      key: "ocmusic",
      supervisor: "Supervisor",
      employees: ["Employee 1", "Employee 2"],
    },
    {
      label: "Bahandi Entertainment",
      key: "bahandi",
      supervisor: "Kenneth",
      employees: ["Lorenz", "Jhason"],
    },
  ] as const;
  const quickLoginGroups: QuickLoginGroup[] = [
    {
      label: "Administration",
      accounts: [
        { label: "Administrator", username: "admin", password: "admin" },
        {
          label: "Analyn",
          username: "hr.admin",
          password: personaPassword,
        },
      ],
    },
    ...personaWorkspaces.map(({ label, key, supervisor, employees }) => ({
      label,
      accounts: [
        {
          label: supervisor,
          username: `supervisor.${key}`,
          password: personaPassword,
        },
        {
          label: employees[0],
          username: `employee.${key}.1`,
          password: personaPassword,
        },
        {
          label: employees[1],
          username: `employee.${key}.2`,
          password: personaPassword,
        },
      ],
    })),
  ];

  const appState = useAppState();
  let username = $state("");
  let password = $state("");
  let error = $state("");
  let loading = $state(false);
  let redirecting = $state(false);

  onMount(() => {
    if (getToken()) {
      window.location.replace("/dashboard");
    }
  });

  async function signIn(user: string, pass: string) {
    error = "";
    loading = true;
    try {
      await appState.signIn(user, pass);
      redirecting = true;
      window.location.replace("/dashboard");
    } catch (err: any) {
      error = err.message || "Login failed";
    } finally {
      loading = false;
    }
  }

  async function submit(e: SubmitEvent) {
    e.preventDefault();
    await signIn(username, password);
  }

  async function quickLogin(account: QuickLoginAccount) {
    username = account.username;
    password = account.password;
    await signIn(username, password);
  }
</script>

{#if loading || redirecting}
  <WorkspaceLoadingScreen
    message="Verifying your account and loading your permissions..."
  />
{:else}
  <div
    class="flex min-h-screen flex-col items-center justify-center gap-4 bg-base-200 p-4 md:flex-row"
  >
    <LoginForm
      bind:username
      bind:password
      onsubmit={submit}
      {loading}
      {error}
    />
    {#if dev}
      <Card.Root class="w-full max-w-sm">
        <Card.Header>
          <Card.Title class="text-2xl">Quick login</Card.Title>
          <Card.Description>
            Dev-only shortcuts to sign in as a persona.
          </Card.Description>
        </Card.Header>
        <Card.Content class="flex flex-col gap-3">
          {#each quickLoginGroups as group (group.label)}
            <div>
              <p class="mb-1 text-xs font-medium text-base-content/60">
                {group.label}
              </p>
              <div class="grid gap-1">
                {#each group.accounts as account (account.username)}
                  <Button
                    variant="outline"
                    size="sm"
                    class="w-full justify-between font-normal"
                    onclick={() => quickLogin(account)}
                    disabled={loading || !account.password}
                  >
                    <span class="truncate">{account.label}</span>
                    <span class="truncate text-xs text-base-content/60">
                      {account.username}
                    </span>
                  </Button>
                {/each}
              </div>
            </div>
          {/each}
        </Card.Content>
      </Card.Root>
    {/if}
  </div>
{/if}
