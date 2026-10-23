<script lang="ts">
  import { onMount } from "svelte";
  import { toast } from "$lib/notifications";
  import * as Tabs from "$lib/components/ui/tabs/index.js";
  import * as Field from "$lib/components/ui/field/index.js";
  import * as Card from "$lib/components/ui/card/index.js";
  import { Input } from "$lib/components/ui/input";
  import * as Select from "$lib/components/ui/select/index.js";
  import { Button } from "$lib/components/ui/button";
  import { Checkbox } from "$lib/components/ui/checkbox";
  import { Badge } from "$lib/components/ui/badge";
  import { apiJSON, toPaginatedResult } from "$lib/api/index.js";
  import { useAppState } from "$lib/app-state.svelte.js";
  import Pagination from "$lib/components/pagination.svelte";

  let destination = $state("");
  let customSlug = $state("");
  let title = $state("");
  let expiresAt = $state("");
  let password = $state("");
  let showPreview = $state(false);
  const appState = useAppState();
  let links = $state<any[]>([]);
  let linksPage = $state(appState.tablePage("short-links"));
  let linksPageSize = $state(20);
  let linksTotal = $state(0);
  let status = $state("all");
  let search = $state("");
  let loading = $state(true);
  let saving = $state(false);
  let selected = $state<any | null>(null);

  const publicBase =
    typeof window !== "undefined" ? window.location.origin : "";

  async function load(targetPage = linksPage) {
    loading = true;
    try {
      const params = new URLSearchParams({
        status,
        page: String(targetPage),
        page_size: String(linksPageSize),
      });
      if (search.trim()) params.set("search", search.trim());
      const res = await apiJSON(`/api/utils/links?${params}`);
      const result = toPaginatedResult<any>(res, targetPage, linksPageSize, [
        "data",
        "items",
      ]);
      if (!result.items.length && result.total > 0 && targetPage > 1) {
        return load(Math.ceil(result.total / linksPageSize));
      }
      links = result.items;
      linksTotal = result.total;
      linksPage = result.page;
      appState.rememberTablePage("short-links", linksPage);
    } catch (e: any) {
      toast.error(e.message || "Failed to load links");
    } finally {
      loading = false;
    }
  }

  function setLinksPage(targetPage: number) {
    linksPage = targetPage;
    appState.rememberTablePage("short-links", targetPage);
    void load(targetPage);
  }

  async function createLink() {
    saving = true;
    try {
      const body: any = { destination_url: destination };
      if (customSlug.trim()) body.custom_slug = customSlug.trim();
      if (title.trim()) body.title = title.trim();
      if (expiresAt) body.expires_at = new Date(expiresAt).toISOString();
      if (password) body.password = password;
      body.show_preview = showPreview;

      await apiJSON("/api/utils/links", {
        method: "POST",
        body: JSON.stringify(body),
      });
      toast.success("Short link created");
      destination = "";
      customSlug = "";
      title = "";
      expiresAt = "";
      password = "";
      showPreview = false;
      setLinksPage(1);
    } catch (e: any) {
      toast.error(e.message || "Failed to create link");
    } finally {
      saving = false;
    }
  }

  async function toggle(link: any) {
    try {
      await apiJSON(`/api/utils/links/${link.id}`, {
        method: "PATCH",
        body: JSON.stringify({ is_active: !link.is_active }),
      });
      toast.success(link.is_active ? "Link deactivated" : "Link activated");
      await load(linksPage);
    } catch (e: any) {
      toast.error(e.message || "Failed to update link");
    }
  }

  async function view(id: string) {
    try {
      selected = await apiJSON(`/api/utils/links/${id}`);
    } catch (e: any) {
      toast.error(e.message || "Failed to load details");
    }
  }

  function copy(slug: string) {
    const url = `${publicBase}/${slug}`;
    navigator.clipboard
      .writeText(url)
      .then(() => toast.success("Copied to clipboard"));
  }

  onMount(load);
</script>

<Tabs.Content value="links">
  <div class="grid gap-6 lg:grid-cols-2">
    <Card.Root>
      <Card.Header>
        <Card.Title>Create Short Link</Card.Title>
      </Card.Header>
      <Card.Content>
        <Field.FieldGroup>
          <Field.Field>
            <Field.FieldLabel for="dest">Destination URL</Field.FieldLabel>
            <Input
              id="dest"
              type="url"
              bind:value={destination}
              placeholder="https://example.com"
            />
          </Field.Field>
          <Field.Field>
            <Field.FieldLabel for="slug"
              >Custom slug (optional)</Field.FieldLabel
            >
            <Input id="slug" bind:value={customSlug} placeholder="my-link" />
          </Field.Field>
          <Field.Field>
            <Field.FieldLabel for="title">Title (optional)</Field.FieldLabel>
            <Input id="title" bind:value={title} placeholder="My link" />
          </Field.Field>
          <Field.Field>
            <Field.FieldLabel for="expires"
              >Expires at (optional)</Field.FieldLabel
            >
            <Input id="expires" type="datetime-local" bind:value={expiresAt} />
          </Field.Field>
          <Field.Field>
            <Field.FieldLabel for="password"
              >Password (optional)</Field.FieldLabel
            >
            <Input id="password" type="password" bind:value={password} />
          </Field.Field>
          <Field.Field class="flex items-center gap-2">
            <Checkbox id="preview" bind:checked={showPreview} />
            <Field.FieldLabel for="preview" class="mb-0"
              >Show preview interstitial</Field.FieldLabel
            >
          </Field.Field>
        </Field.FieldGroup>
        <Button
          class="mt-4"
          onclick={createLink}
          disabled={saving || !destination}
        >
          {saving ? "Creating..." : "Create"}
        </Button>
      </Card.Content>
    </Card.Root>

    <Card.Root>
      <Card.Header>
        <Card.Title>Your Short Links</Card.Title>
      </Card.Header>
      <Card.Content>
        <div class="flex gap-2 mb-4">
          <Select.Root
            type="single"
            bind:value={status}
            onValueChange={() => setLinksPage(1)}
          >
            <Select.Trigger size="md" class="w-auto">
              {status === "all"
                ? "All"
                : status === "active"
                  ? "Active"
                  : status === "inactive"
                    ? "Inactive"
                    : "Expired"}
            </Select.Trigger>
            <Select.Content>
              <Select.Item value="all" label="All">All</Select.Item>
              <Select.Item value="active" label="Active">Active</Select.Item>
              <Select.Item value="inactive" label="Inactive">
                Inactive
              </Select.Item>
              <Select.Item value="expired" label="Expired">Expired</Select.Item>
            </Select.Content>
          </Select.Root>
          <Input
            placeholder="Search slug or title"
            bind:value={search}
            onchange={() => setLinksPage(1)}
          />
        </div>

        {#if loading}
          <p class="text-base-content/60">Loading...</p>
        {:else if links.length === 0}
          <p class="text-base-content/60">No short links yet.</p>
        {:else}
          <table class="table table-zebra">
            <thead>
              <tr>
                <th>Slug</th>
                <th>Title</th>
                <th>Clicks</th>
                <th>Status</th>
                <th class="w-[160px]">Actions</th>
              </tr>
            </thead>
            <tbody>
              {#each links as link (link.id)}
                <tr>
                  <td>{link.slug}</td>
                  <td>{link.title || "—"}</td>
                  <td>{link.click_count}</td>
                  <td>
                    {#if link.is_active}
                      <Badge variant="default">Active</Badge>
                    {:else}
                      <Badge variant="secondary">Inactive</Badge>
                    {/if}
                  </td>
                  <td>
                    <div class="flex gap-1">
                      <Button
                        variant="outline"
                        size="sm"
                        onclick={() => copy(link.slug)}>Copy</Button
                      >
                      <Button
                        variant="outline"
                        size="sm"
                        onclick={() => toggle(link)}
                      >
                        {link.is_active ? "Disable" : "Enable"}
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onclick={() => view(link.id)}>Details</Button
                      >
                    </div>
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
          <Pagination
            page={linksPage}
            pageSize={linksPageSize}
            total={linksTotal}
            {loading}
            pageSizeOptions={[10, 20, 50, 100]}
            onchange={setLinksPage}
            onpagesizechange={(size) => {
              linksPageSize = size;
              setLinksPage(1);
            }}
          />
        {/if}
      </Card.Content>
    </Card.Root>
  </div>

  {#if selected}
    <Card.Root class="mt-6">
      <Card.Header>
        <Card.Title>Link Analytics</Card.Title>
      </Card.Header>
      <Card.Content>
        <p>Total clicks: {selected.data.analytics.total_clicks}</p>
        <p class="text-base-content/60 text-sm mt-1">
          {selected.data.record.destination_url}
        </p>
      </Card.Content>
    </Card.Root>
  {/if}
</Tabs.Content>
