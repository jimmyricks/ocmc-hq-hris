<script lang="ts">
  import { onMount } from "svelte";
  import { dev } from "$app/environment";
  import { goto } from "$app/navigation";
  import { login } from "$lib/api/index.js";
  import { setAuth, getToken } from "$lib/auth";
  import { Button } from "$lib/components/ui/button/index.js";
  import LoginForm from "$lib/components/login-form.svelte";

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

  async function quickLogin() {
    username = "admin";
    password = "admin";
    await signIn(username, password);
  }
</script>

<div
  class="flex min-h-screen flex-col items-center justify-center gap-4 bg-muted p-4"
>
  <LoginForm bind:username bind:password onsubmit={submit} {loading} {error} />
  {#if dev}
    <Button
      variant="outline"
      class="w-full max-w-sm"
      onclick={quickLogin}
      disabled={loading}
    >
      Quick dev login (admin)
    </Button>
  {/if}
</div>
