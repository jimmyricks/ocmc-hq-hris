<script lang="ts">
  import { goto } from "$app/navigation";
  import { useAppState } from "$lib/app-state.svelte.js";
  import * as DropdownMenu from "$lib/components/ui/dropdown-menu/index.js";
  import ChevronsUpDownIcon from "@lucide/svelte/icons/chevrons-up-down";
  import LogOutIcon from "@lucide/svelte/icons/log-out";
  import UserIcon from "@lucide/svelte/icons/user";

  let {
    user,
    onClose,
  }: {
    user: {
      name: string;
      email: string;
      avatar?: string;
    };
    onClose?: () => void;
  } = $props();

  const appState = useAppState();

  function initials(name: string) {
    return name
      .split(" ")
      .map((part) => part[0])
      .filter(Boolean)
      .slice(0, 2)
      .join("")
      .toUpperCase();
  }

  function openProfile() {
    onClose?.();
    goto("/profile");
  }

  function logout() {
    appState.signOut();
    goto("/login");
  }
</script>

<DropdownMenu.Root class="block w-full shrink-0 pt-3">
  <DropdownMenu.Trigger
    class="min-h-12 w-full items-center gap-2.5 rounded-lg px-2 py-2 text-left hover:bg-base-200"
    aria-label="Account menu"
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
    <ChevronsUpDownIcon
      size={16}
      class="shrink-0 text-base-content/60"
      aria-hidden="true"
    />
  </DropdownMenu.Trigger>
  <DropdownMenu.Content side="top" class="w-full">
    <DropdownMenu.Item onclick={openProfile}>
      <UserIcon class="size-4" aria-hidden="true" />
      Profile
    </DropdownMenu.Item>
    <DropdownMenu.Separator />
    <DropdownMenu.Item variant="destructive" onclick={logout}>
      <LogOutIcon class="size-4" aria-hidden="true" />
      Log out
    </DropdownMenu.Item>
  </DropdownMenu.Content>
</DropdownMenu.Root>
