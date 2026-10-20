<script lang="ts">
  import { onMount } from "svelte";
  import { toast } from "$lib/notifications";
  import * as Tabs from "$lib/components/native/tabs/index.js";
  import * as Table from "$lib/components/native/table/index.js";
  import * as Field from "$lib/components/native/field/index.js";
  import * as Card from "$lib/components/native/card/index.js";
  import { Input } from "$lib/components/native/input";
  import { Button } from "$lib/components/native/button";
  import { Checkbox } from "$lib/components/native/checkbox";
  import { Badge } from "$lib/components/native/badge";
  import { apiJSON } from "$lib/api/index.js";

  let destination = $state("");
  let customSlug = $state("");
  let title = $state("");
  let expiresAt = $state("");
  let password = $state("");
  let showPreview = $state(false);
  let links = $state<any[]>([]);
  let status = $state("all");
  let search = $state("");
  let loading = $state(true);
  let saving = $state(false);
  let selected = $state<any | null>(null);

  const publicBase =
    typeof window !== "undefined" ? window.location.origin : "";

  async function load() {
    try {
      const res = await apiJSON(
        `/api/utils/links?status=${status}&search=${encodeURIComponent(search)}`,
      );
      links = res.data?.data ?? [];
    } catch (e: any) {
      toast.error(e.message || "Failed to load links");
    } finally {
      loading = false;
    }
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
      await load();
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
      await load();
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
          <select
            bind:value={status}
            onchange={load}
            class="h-9 rounded-md border px-2 text-sm"
          >
            <option value="all">All</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
            <option value="expired">Expired</option>
          </select>
          <Input
            placeholder="Search slug or title"
            bind:value={search}
            onchange={load}
          />
        </div>

        {#if loading}
          <p class="text-muted-foreground">Loading...</p>
        {:else if links.length === 0}
          <p class="text-muted-foreground">No short links yet.</p>
        {:else}
          <Table.Root>
            <Table.Header>
              <Table.Row>
                <Table.Head>Slug</Table.Head>
                <Table.Head>Title</Table.Head>
                <Table.Head>Clicks</Table.Head>
                <Table.Head>Status</Table.Head>
                <Table.Head class="w-[160px]">Actions</Table.Head>
              </Table.Row>
            </Table.Header>
            <Table.Body>
              {#each links as link (link.id)}
                <Table.Row>
                  <Table.Cell>{link.slug}</Table.Cell>
                  <Table.Cell>{link.title || "—"}</Table.Cell>
                  <Table.Cell>{link.click_count}</Table.Cell>
                  <Table.Cell>
                    {#if link.is_active}
                      <Badge variant="default">Active</Badge>
                    {:else}
                      <Badge variant="secondary">Inactive</Badge>
                    {/if}
                  </Table.Cell>
                  <Table.Cell>
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
                  </Table.Cell>
                </Table.Row>
              {/each}
            </Table.Body>
          </Table.Root>
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
        <p class="text-muted-foreground text-sm mt-1">
          {selected.data.record.destination_url}
        </p>
      </Card.Content>
    </Card.Root>
  {/if}
</Tabs.Content>
