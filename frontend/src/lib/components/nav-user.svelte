<script lang="ts">
  import { clearAuth } from "$lib/auth";
  import { goto } from "$app/navigation";
  import { Button } from "$lib/components/ui/button/index.js";
  import LogOutIcon from "@lucide/svelte/icons/log-out";

  let {
    user,
  }: {
    user: {
      name: string;
      email: string;
      avatar?: string;
    };
  } = $props();

  function initials(name: string) {
    return name
      .split(" ")
      .map((part) => part[0])
      .filter(Boolean)
      .slice(0, 2)
      .join("")
      .toUpperCase();
  }

  function logout() {
    clearAuth();
    goto("/login");
  }
</script>

<div
  class="flex min-h-14 items-center gap-2.5 border-t border-base-300 px-1 pt-3"
>
  {#if user.avatar}
    <img
      class="size-8 shrink-0 rounded-lg border border-base-300 object-cover"
      src={user.avatar}
      alt=""
    />
  {:else}
    <span
      class="grid size-8 shrink-0 place-items-center rounded-lg bg-primary/10 text-xs font-semibold text-primary"
    >
      {initials(user.name)}
    </span>
  {/if}
  <span class="grid min-w-0 flex-1 gap-0.5">
    <strong class="truncate text-xs font-medium text-base-content"
      >{user.name}</strong
    >
    <small class="truncate text-xs text-base-content/60">{user.email}</small>
  </span>
  <Button
    variant="ghost"
    size="sm" icon
    aria-label="Log out"
    title="Log out"
    onclick={logout}
  >
    <LogOutIcon size={16} aria-hidden="true" />
  </Button>
</div>
