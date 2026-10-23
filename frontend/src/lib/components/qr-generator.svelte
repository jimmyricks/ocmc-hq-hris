<script lang="ts">
  import { onMount } from "svelte";
  import { toast } from "$lib/notifications";
  import DOMPurify from "dompurify";
  import * as Tabs from "$lib/components/ui/tabs/index.js";
  import * as Card from "$lib/components/ui/card/index.js";
  import * as Field from "$lib/components/ui/field/index.js";
  import { Input } from "$lib/components/ui/input";
  import { Textarea } from "$lib/components/ui/textarea";
  import { Button } from "$lib/components/ui/button";
  import * as Select from "$lib/components/ui/select/index.js";
  import { apiFetch, apiJSON, toPaginatedResult } from "$lib/api/index.js";
  import { useAppState } from "$lib/app-state.svelte.js";
  import Pagination from "$lib/components/pagination.svelte";

  let sourceType = $state("url");
  let sourceValue = $state("");
  let shortLinkId = $state("");
  let ecLevel = $state("M");
  let size = $state(256);
  let format = $state("svg");
  let fgColor = $state("#000000");
  let bgColor = $state("#ffffff");

  let dataUrl = $state<string | null>(null);
  let recordId = $state<string | null>(null);
  const appState = useAppState();
  let history = $state<any[]>([]);
  let historyPage = $state(appState.tablePage("qr-history"));
  let historyPageSize = $state(20);
  let historyTotal = $state(0);
  let shortLinks = $state<any[]>([]);
  let loading = $state(true);
  let generating = $state(false);

  function toDataUrl(contentType: string, body: string | Uint8Array) {
    if (typeof body === "string") {
      const b64 = btoa(unescape(encodeURIComponent(body)));
      return `data:${contentType};base64,${b64}`;
    }
    let binary = "";
    const bytes = new Uint8Array(body);
    for (let i = 0; i < bytes.byteLength; i++) {
      binary += String.fromCharCode(bytes[i]);
    }
    return `data:${contentType};base64,${btoa(binary)}`;
  }

  async function loadHistory(targetPage = historyPage) {
    loading = true;
    try {
      const [qrRes, linksRes] = await Promise.all([
        apiJSON(
          `/api/utils/qr?page=${targetPage}&page_size=${historyPageSize}`,
        ),
        apiJSON("/api/utils/links?status=active&page=1&page_size=100"),
      ]);
      const result = toPaginatedResult<any>(
        qrRes,
        targetPage,
        historyPageSize,
        ["data", "items"],
      );
      if (!result.items.length && result.total > 0 && targetPage > 1) {
        return loadHistory(Math.ceil(result.total / historyPageSize));
      }
      history = result.items;
      historyTotal = result.total;
      historyPage = result.page;
      appState.rememberTablePage("qr-history", historyPage);
      shortLinks = linksRes.data?.data ?? [];
    } catch (e: any) {
      toast.error(e.message || "Failed to load history");
    } finally {
      loading = false;
    }
  }

  function setHistoryPage(targetPage: number) {
    historyPage = targetPage;
    appState.rememberTablePage("qr-history", targetPage);
    void loadHistory(targetPage);
  }

  function sanitizeSvg(svg: string) {
    return DOMPurify.sanitize(svg, { USE_PROFILES: { svg: true } });
  }

  async function generate() {
    generating = true;
    try {
      const payload: any = {
        source_type: sourceType,
        error_correction_level: ecLevel,
        size,
        format,
        fg_color: fgColor,
        bg_color: bgColor,
      };

      if (sourceType === "short_link") {
        payload.short_link_id = shortLinkId;
      } else {
        payload.source_value = sourceValue;
      }

      const res = await apiJSON("/api/utils/qr/generate", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      const result = res.data;
      recordId = result.record.id;
      const raw = result.data_url;
      if (format === "svg") {
        const svg = atob(raw.split(",")[1]);
        const clean = sanitizeSvg(svg);
        dataUrl = toDataUrl("image/svg+xml", clean);
      } else {
        dataUrl = raw;
      }
      toast.success("QR code generated");
      setHistoryPage(1);
    } catch (e: any) {
      toast.error(e.message || "Failed to generate QR");
    } finally {
      generating = false;
    }
  }

  async function download(id: string, fmt: string) {
    try {
      const res = await apiFetch(`/api/utils/qr/${id}/download?format=${fmt}`);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `qr-${id}.${fmt}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e: any) {
      toast.error(e.message || "Download failed");
    }
  }

  async function reRender(item: any) {
    try {
      const res = await apiJSON(`/api/utils/qr/${item.id}`);
      const raw = res.data.data_url;
      const isSvg = item.format === "svg";
      const url = isSvg
        ? toDataUrl("image/svg+xml", sanitizeSvg(atob(raw.split(",")[1])))
        : raw;
      dataUrl = url;
      recordId = item.id;
      sourceType = item.source_type;
      sourceValue = item.source_value;
      ecLevel = item.error_correction_level;
      size = item.size;
      format = item.format;
      fgColor = item.fg_color;
      bgColor = item.bg_color;
    } catch (e: any) {
      toast.error(e.message || "Failed to re-render");
    }
  }

  onMount(loadHistory);
</script>

<Tabs.Content value="qr">
  <div class="grid gap-6 lg:grid-cols-2">
    <Card.Root>
      <Card.Header>
        <Card.Title>Generate QR Code</Card.Title>
      </Card.Header>
      <Card.Content>
        <Field.FieldGroup>
          <Field.Field>
            <Field.FieldLabel>Source Type</Field.FieldLabel>
            <Select.Root type="single" bind:value={sourceType}>
              <Select.Trigger>{sourceType}</Select.Trigger>
              <Select.Content>
                <Select.Item value="url">URL</Select.Item>
                <Select.Item value="text">Text</Select.Item>
                <Select.Item value="short_link">Short Link</Select.Item>
              </Select.Content>
            </Select.Root>
          </Field.Field>

          {#if sourceType === "short_link"}
            <Field.Field>
              <Field.FieldLabel>Short Link</Field.FieldLabel>
              <Select.Root type="single" bind:value={shortLinkId}>
                <Select.Trigger
                  >{shortLinks.find((l) => l.id === shortLinkId)?.slug ||
                    "Select link"}</Select.Trigger
                >
                <Select.Content>
                  {#each shortLinks as link (link.id)}
                    <Select.Item value={link.id}
                      >{link.slug} — {link.title ||
                        link.destination_url}</Select.Item
                    >
                  {/each}
                </Select.Content>
              </Select.Root>
            </Field.Field>
          {:else if sourceType === "text"}
            <Field.Field>
              <Field.FieldLabel for="qr-text">Text</Field.FieldLabel>
              <Textarea id="qr-text" bind:value={sourceValue} rows={4} />
            </Field.Field>
          {:else}
            <Field.Field>
              <Field.FieldLabel for="qr-url">URL</Field.FieldLabel>
              <Input
                id="qr-url"
                type="url"
                bind:value={sourceValue}
                placeholder="https://example.com"
              />
            </Field.Field>
          {/if}

          <Field.Field>
            <Field.FieldLabel>Error Correction</Field.FieldLabel>
            <Select.Root type="single" bind:value={ecLevel}>
              <Select.Trigger>{ecLevel}</Select.Trigger>
              <Select.Content>
                <Select.Item value="L">L (Low)</Select.Item>
                <Select.Item value="M">M (Medium)</Select.Item>
                <Select.Item value="Q">Q (Quartile)</Select.Item>
                <Select.Item value="H">H (High)</Select.Item>
              </Select.Content>
            </Select.Root>
          </Field.Field>

          <Field.Field>
            <Field.FieldLabel for="qr-size">Size (px)</Field.FieldLabel>
            <Input
              id="qr-size"
              type="number"
              bind:value={size}
              min={50}
              max={1000}
            />
          </Field.Field>

          <Field.Field>
            <Field.FieldLabel>Format</Field.FieldLabel>
            <Select.Root type="single" bind:value={format}>
              <Select.Trigger>{format.toUpperCase()}</Select.Trigger>
              <Select.Content>
                <Select.Item value="svg">SVG</Select.Item>
                <Select.Item value="png">PNG</Select.Item>
              </Select.Content>
            </Select.Root>
          </Field.Field>

          <Field.Field>
            <Field.FieldLabel for="qr-fg">Foreground Color</Field.FieldLabel>
            <Input id="qr-fg" type="color" bind:value={fgColor} />
          </Field.Field>

          <Field.Field>
            <Field.FieldLabel for="qr-bg">Background Color</Field.FieldLabel>
            <Input id="qr-bg" type="color" bind:value={bgColor} />
          </Field.Field>
        </Field.FieldGroup>

        <Button class="mt-4" onclick={generate} disabled={generating}>
          {generating ? "Generating..." : "Generate"}
        </Button>
      </Card.Content>
    </Card.Root>

    <Card.Root>
      <Card.Header>
        <Card.Title>Preview</Card.Title>
      </Card.Header>
      <Card.Content class="flex flex-col items-center gap-4">
        {#if dataUrl}
          <img src={dataUrl} alt="QR Code" class="border rounded-md" />
          {#if recordId}
            <Button
              variant="outline"
              onclick={() => download(recordId!, format)}
            >
              Download {format.toUpperCase()}
            </Button>
          {/if}
        {:else}
          <p class="text-base-content/60">Generated QR will appear here</p>
        {/if}
      </Card.Content>
    </Card.Root>
  </div>

  <Card.Root class="mt-6">
    <Card.Header>
      <Card.Title>History</Card.Title>
    </Card.Header>
    <Card.Content>
      {#if loading}
        <p class="text-base-content/60">Loading...</p>
      {:else if history.length === 0}
        <p class="text-base-content/60">No QR codes yet.</p>
      {:else}
        <table class="table table-zebra">
          <thead>
            <tr>
              <th>Type</th>
              <th>Source</th>
              <th>Format</th>
              <th>Size</th>
              <th class="w-[180px]">Actions</th>
            </tr>
          </thead>
          <tbody>
            {#each history as item (item.id)}
              <tr>
                <td>{item.source_type}</td>
                <td class="max-w-[200px] truncate"
                  >{item.source_value}</td
                >
                <td>{item.format}</td>
                <td>{item.size}</td>
                <td>
                  <div class="flex gap-1">
                    <Button
                      variant="outline"
                      size="sm"
                      onclick={() => reRender(item)}>View</Button
                    >
                    <Button
                      variant="outline"
                      size="sm"
                      onclick={() => download(item.id, item.format)}
                      >Download</Button
                    >
                  </div>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
        <Pagination
          page={historyPage}
          pageSize={historyPageSize}
          total={historyTotal}
          {loading}
          pageSizeOptions={[10, 20, 50, 100]}
          onchange={setHistoryPage}
          onpagesizechange={(size) => {
            historyPageSize = size;
            setHistoryPage(1);
          }}
        />
      {/if}
    </Card.Content>
  </Card.Root>
</Tabs.Content>
