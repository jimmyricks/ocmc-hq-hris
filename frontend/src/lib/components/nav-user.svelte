<script lang="ts">
  import { clearAuth } from "$lib/auth";
  import { goto } from "$app/navigation";
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

<div class="hq-profile">
  {#if user.avatar}
    <img class="hq-profile__avatar" src={user.avatar} alt="" />
  {:else}
    <span class="hq-profile__avatar hq-profile__initials">
      {initials(user.name)}
    </span>
  {/if}
  <span class="hq-profile__copy">
    <strong>{user.name}</strong>
    <small>{user.email}</small>
  </span>
  <button
    class="hq-profile__logout"
    type="button"
    aria-label="Log out"
    title="Log out"
    onclick={logout}
  >
    <LogOutIcon size={16} />
  </button>
</div>

<style>
  .hq-profile {
    display: flex;
    min-height: 55px;
    align-items: center;
    gap: 10px;
    border-top: 1px solid #e6eaf0;
    padding: 11px 3px 1px;
  }
  .hq-profile__avatar {
    display: grid;
    width: 33px;
    height: 33px;
    flex: none;
    place-items: center;
    border: 1px solid #dce4f1;
    border-radius: 9px;
    background: #edf2ff;
    color: #2457d6;
    font-size: 11px;
    font-weight: 750;
  }
  .hq-profile__copy {
    display: grid;
    min-width: 0;
    flex: 1;
    gap: 2px;
  }
  .hq-profile__copy strong,
  .hq-profile__copy small {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .hq-profile__copy strong {
    color: #344256;
    font-size: 12px;
    font-weight: 650;
  }
  .hq-profile__copy small {
    color: #8792a2;
    font-size: 10px;
  }
  .hq-profile__logout {
    display: grid;
    width: 30px;
    height: 30px;
    flex: none;
    place-items: center;
    border: 1px solid transparent;
    border-radius: 7px;
    background: transparent;
    color: #7a8798;
    cursor: pointer;
  }
  .hq-profile__logout:hover {
    border-color: #e3e8ef;
    background: #f5f7fa;
    color: #ad2635;
  }
</style>
