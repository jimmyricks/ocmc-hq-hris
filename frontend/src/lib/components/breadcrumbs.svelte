<script lang="ts">
  type BreadcrumbItem = {
    label: string;
    href?: string;
  };

  let {
    items = [],
    class: className = "",
    "aria-label": ariaLabel = "Breadcrumb",
  }: {
    items?: BreadcrumbItem[];
    class?: string;
    "aria-label"?: string;
  } = $props();
</script>

<nav aria-label={ariaLabel} class="breadcrumbs min-w-0 text-sm {className}">
  <ul>
    {#each items as item, index (item.href ?? `${item.label}-${index}`)}
      <li>
        {#if item.href && index < items.length - 1}
          <a
            class="text-base-content/60 no-underline hover:text-primary"
            href={item.href}>{item.label}</a
          >
        {:else}
          <span
            class="truncate font-medium text-base-content"
            aria-current="page">{item.label}</span
          >
        {/if}
      </li>
    {/each}
  </ul>
</nav>
