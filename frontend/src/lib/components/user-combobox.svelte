<script lang="ts">
  import { onDestroy } from "svelte";
  import ChevronDownIcon from "@lucide/svelte/icons/chevron-down";
  import type { User } from "$lib/task-manager/types.js";

  let {
    value = $bindable(""),
    selectedLabel = "",
    fetchOptions,
    onSelect,
    id = "user-lookup",
    placeholder = "Search users...",
    disabled = false,
  }: {
    value?: string;
    selectedLabel?: string;
    fetchOptions: (search: string) => Promise<User[]>;
    onSelect?: (user: User) => void;
    id?: string;
    placeholder?: string;
    disabled?: boolean;
  } = $props();

  let query = $state("");
  let options = $state<User[]>([]);
  let activeIndex = $state(-1);
  let open = $state(false);
  let searching = $state(false);
  let lookupError = $state(false);
  let syncedValue = $state("");
  let requestId = 0;
  let debounceTimer: ReturnType<typeof setTimeout> | undefined;

  onDestroy(() => {
    clearTimeout(debounceTimer);
    requestId += 1;
  });

  $effect(() => {
    const currentValue = value;
    const label = selectedLabel;
    if (currentValue !== syncedValue) {
      syncedValue = currentValue;
      query = label;
    }
  });

  async function loadOptions(search: string) {
    const request = ++requestId;
    searching = true;
    lookupError = false;
    try {
      const results = await fetchOptions(search);
      if (request === requestId) {
        options = results;
        activeIndex = results.length ? 0 : -1;
      }
    } catch {
      if (request === requestId) {
        options = [];
        activeIndex = -1;
        lookupError = true;
      }
    } finally {
      if (request === requestId) searching = false;
    }
  }

  function scheduleSearch(search: string) {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => void loadOptions(search), 250);
  }

  function handleInput(event: Event) {
    query = (event.currentTarget as HTMLInputElement).value;
    requestId += 1;
    options = [];
    activeIndex = -1;
    searching = true;
    open = true;
    scheduleSearch(query);
  }

  function selectOption(user: User) {
    clearTimeout(debounceTimer);
    requestId += 1;
    query = user.full_name || user.username || user.email;
    syncedValue = user.id;
    value = user.id;
    open = false;
    onSelect?.(user);
  }

  function openOptions() {
    if (disabled) return;
    open = true;
    const search = value && query === selectedLabel ? "" : query;
    void loadOptions(search);
  }

  function handleKeydown(event: KeyboardEvent) {
    if (event.key === "Escape") {
      open = false;
      return;
    }
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      if (!open) {
        openOptions();
      } else if (options.length) {
        const direction = event.key === "ArrowDown" ? 1 : -1;
        activeIndex =
          (activeIndex + direction + options.length) % options.length;
      }
    } else if (event.key === "Enter" && open && activeIndex >= 0) {
      event.preventDefault();
      const user = options[activeIndex];
      if (user) selectOption(user);
    }
  }
</script>

<div class="relative w-full">
  <label class="input w-full border-base-300" for={id}>
    <input
      {id}
      type="text"
      role="combobox"
      aria-autocomplete="list"
      aria-expanded={open}
      aria-controls="{id}-options"
      aria-activedescendant={open && activeIndex >= 0
        ? `${id}-option-${activeIndex}`
        : undefined}
      autocomplete="off"
      {placeholder}
      {disabled}
      bind:value={query}
      oninput={handleInput}
      onclick={() => {
        if (!open) openOptions();
      }}
      onkeydown={handleKeydown}
      onblur={() => {
        setTimeout(() => (open = false), 100);
      }}
    />
    <ChevronDownIcon
      size={16}
      class="shrink-0 cursor-pointer opacity-60"
      aria-hidden="true"
      onmousedown={(event) => event.preventDefault()}
      onclick={(event) => {
        event.stopPropagation();
        if (open) {
          open = false;
        } else {
          openOptions();
        }
      }}
    />
  </label>
  {#if open}
    <ul
      id="{id}-options"
      role="listbox"
      class="absolute z-50 mt-1 max-h-60 w-full overflow-y-auto rounded-lg border border-base-300 bg-base-100 p-1 shadow-lg"
    >
      {#if searching && !options.length}
        <li class="px-3 py-2 text-sm text-base-content/60">Searching...</li>
      {:else if lookupError}
        <li class="px-3 py-2 text-sm text-error">Unable to load users.</li>
      {:else if !options.length}
        <li class="px-3 py-2 text-sm text-base-content/60">No users found.</li>
      {:else}
        {#each options as user, index (user.id)}
          <li>
            <button
              id="{id}-option-{index}"
              type="button"
              role="option"
              aria-selected={index === activeIndex}
              class="flex w-full flex-col items-start rounded-md px-3 py-2 text-left text-sm hover:bg-base-200"
              class:bg-base-200={index === activeIndex}
              onmousedown={(event) => event.preventDefault()}
              onclick={() => selectOption(user)}
              onmouseenter={() => (activeIndex = index)}
            >
              <span class="w-full truncate font-medium">
                {user.full_name || user.username || user.email}
              </span>
              {#if user.email}
                <span class="w-full truncate text-xs text-base-content/60">
                  {user.email}
                </span>
              {/if}
            </button>
          </li>
        {/each}
      {/if}
    </ul>
  {/if}
</div>
