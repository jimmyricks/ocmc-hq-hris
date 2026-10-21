<script lang="ts">
  import { onMount } from "svelte";
  import { dev } from "$app/environment";
  import { goto } from "$app/navigation";
  import { env } from "$env/dynamic/public";
  import { login } from "$lib/api/index.js";
  import { setAuth, getToken } from "$lib/auth";
  import { Button } from "$lib/components/ui/button/index.js";
  import * as DropdownMenu from "$lib/components/ui/dropdown-menu/index.js";
  import LoginForm from "$lib/components/login-form.svelte";

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

  let username = $state("");
  let password = $state("");
  let error = $state("");
  let loading = $state(false);

  onMount(() => {
    if (getToken()) {
      goto("/dashboard");
    }
  });

  async function signIn(user: string, pass: string) {
    error = "";
    loading = true;
    try {
      const res = await login(user, pass);
      setAuth(res.access_token, res.user, res.refresh_token);
      goto("/dashboard");
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

<div
  class="flex min-h-screen flex-col items-center justify-center gap-4 bg-base-200 p-4"
>
  <LoginForm bind:username bind:password onsubmit={submit} {loading} {error} />
  {#if dev}
    <DropdownMenu.Root class="w-full max-w-sm">
      <DropdownMenu.Trigger class="w-full">
        {#snippet child({ props })}
          <Button
            {...props}
            variant="outline"
            class="w-full"
            disabled={loading}
          >
            Quick login
          </Button>
        {/snippet}
      </DropdownMenu.Trigger>
      <DropdownMenu.Content
        class="max-h-[70vh] w-full overflow-y-auto"
        align="center"
      >
        {#each quickLoginGroups as group (group.label)}
          <DropdownMenu.Label>{group.label}</DropdownMenu.Label>
          {#each group.accounts as account (account.username)}
            <DropdownMenu.Item
              onclick={() => quickLogin(account)}
              disabled={loading || !account.password}
            >
              <span class="min-w-0">
                <span class="block truncate">{account.label}</span>
                <span
                  class="block truncate text-xs font-normal text-base-content/60"
                >
                  {account.username}
                </span>
              </span>
            </DropdownMenu.Item>
          {/each}
        {/each}
      </DropdownMenu.Content>
    </DropdownMenu.Root>
  {/if}
</div>
