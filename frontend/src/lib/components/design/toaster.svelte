<script lang="ts">
  import { fly } from "svelte/transition";
  import { dismiss, notices } from "$lib/notifications";
</script>

<div class="ds-toaster" aria-live="polite" aria-relevant="additions">
  {#each $notices as notice (notice.id)}
    <div
      class="ds-notice ds-notice--{notice.kind}"
      role={notice.kind === "error" ? "alert" : "status"}
      in:fly={{ y: 8, duration: 150 }}
    >
      <span class="ds-notice__mark" aria-hidden="true">
        {notice.kind === "success" ? "✓" : "!"}
      </span>
      <span>{notice.message}</span>
      <button type="button" aria-label="Dismiss notification" onclick={() => dismiss(notice.id)}>×</button>
    </div>
  {/each}
</div>

<style>
  .ds-toaster {
    position: fixed;
    right: 20px;
    bottom: 20px;
    z-index: 100;
    display: flex;
    width: min(390px, calc(100vw - 32px));
    flex-direction: column;
    gap: 8px;
  }
  .ds-notice {
    display: flex;
    align-items: center;
    gap: 10px;
    border: 1px solid #dbe1e9;
    border-radius: 10px;
    background: #fff;
    padding: 11px 12px;
    color: #344256;
    font-size: 13px;
    box-shadow: 0 10px 28px rgb(32 42 56 / 12%);
  }
  .ds-notice--success .ds-notice__mark {
    background: #e3f5ec;
    color: #1b8051;
  }
  .ds-notice--error .ds-notice__mark {
    background: #fae8ea;
    color: #ad2635;
  }
  .ds-notice__mark {
    display: grid;
    width: 21px;
    height: 21px;
    flex: none;
    place-items: center;
    border-radius: 50%;
    font-weight: 800;
  }
  .ds-notice button {
    margin-left: auto;
    border: 0;
    background: transparent;
    color: #7a8798;
    font-size: 18px;
    cursor: pointer;
  }
</style>
