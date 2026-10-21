<script lang="ts">
  import { fly } from "svelte/transition";
  import { dismiss, notices } from "$lib/notifications";
  import { Button } from "$lib/components/ui/button/index.js";
  import CheckIcon from "@lucide/svelte/icons/check";
  import TriangleAlertIcon from "@lucide/svelte/icons/triangle-alert";
  import XIcon from "@lucide/svelte/icons/x";
</script>

<div
  class="fixed bottom-5 right-5 z-[100] flex w-[min(390px,calc(100vw-2rem))] flex-col gap-2"
  aria-live="polite"
  aria-relevant="additions"
>
  {#each $notices as notice (notice.id)}
    <div
      class="alert alert-soft flex items-center gap-3 border border-base-300 bg-base-100 text-base-content shadow-xl {notice.kind ===
      'success'
        ? 'border-success/30'
        : 'border-error/30'}"
      role={notice.kind === "error" ? "alert" : "status"}
      in:fly={{ y: 8, duration: 150 }}
    >
      <span
        class="grid size-6 shrink-0 place-items-center rounded-full bg-base-content/5 {notice.kind ===
        'success'
          ? 'text-success'
          : 'text-error'}"
        aria-hidden="true"
      >
        {#if notice.kind === "success"}
          <CheckIcon size={16} />
        {:else}
          <TriangleAlertIcon size={16} />
        {/if}
      </span>
      <span class="min-w-0 flex-1 text-sm">{notice.message}</span>
      <Button
        variant="ghost"
        size="sm" icon
        aria-label="Dismiss notification"
        onclick={() => dismiss(notice.id)}
      >
        <XIcon size={16} aria-hidden="true" />
      </Button>
    </div>
  {/each}
</div>
