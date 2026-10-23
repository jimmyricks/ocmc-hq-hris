<script lang="ts">
  let {
    message = "Checking your access and preparing your workspace...",
  }: { message?: string } = $props();
</script>

<div
  class="grid min-h-screen place-items-center bg-base-200 px-5 text-base-content"
  role="status"
  aria-live="polite"
  aria-busy="true"
>
  <div class="w-full max-w-sm text-center">
    <div
      class="mx-auto mb-6 grid size-14 place-items-center rounded-2xl bg-primary text-xl font-black tracking-tight text-primary-content shadow-lg shadow-primary/20"
      aria-hidden="true"
    >
      OC
    </div>
    <span class="loading loading-spinner loading-md text-primary"></span>
    <p class="mt-5 text-xs font-semibold uppercase tracking-[0.18em] text-base-content/50">
      OCMC HQ
    </p>
    <h1 class="mt-2 text-xl font-semibold tracking-tight">
      Preparing your workspace
    </h1>
    <p class="mt-2 text-sm leading-6 text-base-content/60">{message}</p>
    <div class="mx-auto mt-7 h-1 w-40 overflow-hidden rounded-full bg-base-300">
      <div class="h-full w-2/5 animate-pulse rounded-full bg-primary"></div>
    </div>
  </div>
</div>
