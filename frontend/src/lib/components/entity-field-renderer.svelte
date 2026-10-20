<script lang="ts">
  import { createEventDispatcher } from "svelte";
  import Input from "$lib/components/ui/input/input.svelte";
  import Textarea from "$lib/components/ui/textarea/textarea.svelte";
  import Checkbox from "$lib/components/ui/checkbox/checkbox.svelte";
  import Button from "$lib/components/ui/button/button.svelte";
  import Field from "$lib/components/ui/field/field.svelte";
  import Label from "$lib/components/ui/label/label.svelte";
  import { Calendar as CalendarIcon } from "phosphor-svelte";
  import Calendar from "$lib/components/ui/calendar/calendar.svelte";
  import Popover from "$lib/components/ui/popover/popover.svelte";
  import PopoverContent from "$lib/components/ui/popover/popover-content.svelte";
  import PopoverTrigger from "$lib/components/ui/popover/popover-trigger.svelte";
  import * as Select from "$lib/components/ui/select/index.js";
  import { parseDate, type CalendarDate } from "@internationalized/date";

  export interface FieldMeta {
    name: string;
    label: string;
    field_type: string;
    placeholder?: string;
    description?: string;
    required?: boolean;
    options?: any;
    link_entity?: string;
    child_entity?: string;
    parent_entity?: string;
    child_parent_fk_field?: string;
    query?: { key: string };
    filter_by?: string;
  }

  interface Props {
    field: FieldMeta;
    value: any;
    disabled?: boolean;
    loading?: boolean;
    linkOptions?: Record<string, any[]>;
    linkTitles?: Record<string, string>;
    entityName?: string;
    recordId?: string;
    formState?: Record<string, any>;
  }

  let {
    field,
    value = $bindable(),
    disabled = false,
    loading = false,
    linkOptions = {},
    linkTitles = {},
    entityName,
    recordId,
    formState = {},
  }: Props = $props();

  const dispatch = createEventDispatcher();

  // Date handling
  let datePopoverOpen = $state(false);
  let selectedDate = $state<CalendarDate | undefined>();

  $effect(() => {
    if (
      value &&
      (field.field_type === "date" || field.field_type === "datetime")
    ) {
      try {
        selectedDate = parseDate(String(value));
      } catch {
        selectedDate = undefined;
      }
    } else {
      selectedDate = undefined;
    }
  });

  $effect(() => {
    if (selectedDate) {
      value = selectedDate.toString();
    }
  });

  function sentenceCase(str: string): string {
    return str.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  }

  // Select options
  const selectItems = $derived.by(() => {
    const raw = field.options;
    if (!raw) return [];

    if (Array.isArray(raw)) {
      if (raw.length === 0) return [];
      if (typeof raw[0] === "string") {
        return raw.map((v: string) => ({ value: v, label: sentenceCase(v) }));
      }
      return raw.map((item: any) => ({
        value: item.value,
        label: sentenceCase(item.label || item.value),
      }));
    }

    if (typeof raw === "string") {
      return raw
        .split("\n")
        .map((s) => s.trim())
        .filter(Boolean)
        .map((v) => ({ value: v, label: sentenceCase(v) }));
    }

    return [];
  });

  // Link field handling
  const linkItems = $derived.by(() => {
    const entity = field.link_entity;
    if (!entity || !linkOptions[entity]) return [];
    return linkOptions[entity];
  });

  const getLinkDisplayLabel = (val: any): string => {
    if (!val || !field.link_entity) return "";
    const key = `${field.link_entity}::${val}`;
    if (linkTitles[key]) return linkTitles[key];
    const opt = linkItems.find((o: any) => String(o.value) === String(val));
    return opt?.label || String(val);
  };

  // Parent-child link handling
  const parentChildItems = $derived.by(() => {
    const entity = field.child_entity;
    if (!entity || !linkOptions[entity]) return [];
    return linkOptions[entity];
  });

  const getParentChildDisplayLabel = (val: any): string => {
    if (!val || !field.child_entity) return "";
    const key = `${field.child_entity}::${val}`;
    return linkTitles[key] || String(val);
  };

  // Query link handling
  const queryLinkItems = $derived.by(() => {
    const entity = field.query?.key;
    if (!entity || !linkOptions[entity]) return [];
    return linkOptions[entity];
  });

  const getQueryLinkDisplayLabel = (val: any): string => {
    if (!val) return "";
    const opt = queryLinkItems.find(
      (o: any) => String(o.value) === String(val),
    );
    return opt?.label || String(val);
  };

  // Get placeholder text
  const placeholder = $derived(
    field.placeholder || `Enter ${field.label.toLowerCase()}`,
  );
</script>

<div class="relative w-full">
  {#if field.field_type === "string" || field.field_type === "String"}
    <Input
      bind:value
      {placeholder}
      required={field.required}
      {disabled}
      class="w-full"
    />
  {:else if field.field_type === "integer" || field.field_type === "int" || field.field_type === "float"}
    <Input
      bind:value
      type="number"
      step={field.field_type === "float" ? 0.01 : 1}
      {placeholder}
      required={field.required}
      {disabled}
      class="w-full"
    />
  {:else if field.field_type === "currency" || field.field_type === "money"}
    <Input
      bind:value
      type="number"
      step="0.01"
      {placeholder}
      required={field.required}
      {disabled}
      class="w-full"
    />
  {:else if field.field_type === "date"}
    <div class="relative">
      <Input
        bind:value
        {placeholder}
        required={field.required}
        {disabled}
        class="w-full pr-10"
      />
      <Popover bind:open={datePopoverOpen}>
        <PopoverTrigger>
          <Button
            variant="ghost"
            size="icon"
            class="absolute right-0 top-0 h-8 w-8"
            {disabled}
          >
            <CalendarIcon class="h-4 w-4" />
          </Button>
        </PopoverTrigger>
        <PopoverContent class="w-auto p-0">
          <Calendar bind:value={selectedDate} type="single" initialFocus />
        </PopoverContent>
      </Popover>
    </div>
  {:else if field.field_type === "datetime"}
    <div class="relative">
      <Input
        bind:value
        type="datetime-local"
        {placeholder}
        required={field.required}
        {disabled}
        class="w-full pr-10"
      />
      <Popover bind:open={datePopoverOpen}>
        <PopoverTrigger>
          <Button
            variant="ghost"
            size="icon"
            class="absolute right-0 top-0 h-8 w-8"
            {disabled}
          >
            <CalendarIcon class="h-4 w-4" />
          </Button>
        </PopoverTrigger>
        <PopoverContent class="w-auto p-0">
          <Calendar bind:value={selectedDate} type="single" initialFocus />
        </PopoverContent>
      </Popover>
    </div>
  {:else if field.field_type === "boolean"}
    {@const booleanValue = value ?? false}
    <Checkbox
      checked={booleanValue}
      onCheckedChange={(checked: boolean) => (value = checked)}
      {disabled}
    />
  {:else if field.field_type === "select"}
    {@const selectedLabel =
      selectItems.find((i) => i.value === value)?.label ||
      field.placeholder ||
      `Select ${field.label.toLowerCase()}`}
    <Select.Root
      type="single"
      value={value ?? ""}
      {disabled}
      onValueChange={(v) => (value = v)}
    >
      <Select.Trigger class="w-full">
        <span class="truncate">{selectedLabel}</span>
      </Select.Trigger>
      <Select.Content class="p-1">
        <Select.Item
          value=""
          label={field.placeholder || `Select ${field.label.toLowerCase()}`}
        >
          {field.placeholder || `Select ${field.label.toLowerCase()}`}
        </Select.Item>
        {#each selectItems as item (item.value)}
          <Select.Item value={item.value} label={item.label}>
            {item.label}
          </Select.Item>
        {/each}
      </Select.Content>
    </Select.Root>
  {:else if field.field_type === "text"}
    <Textarea
      bind:value
      {placeholder}
      required={field.required}
      rows={4}
      {disabled}
      class="w-full"
    />
  {:else if field.field_type === "link" && field.link_entity}
    <div class="flex items-center gap-2">
      <select
        bind:value
        {disabled}
        required={field.required}
        class="flex-1 w-full h-8 rounded-none border border-input bg-transparent px-2.5 py-1 text-xs outline-none focus-visible:ring-1 disabled:cursor-not-allowed disabled:opacity-50"
      >
        <option value="">Select {field.label.toLowerCase()}</option>
        {#each linkItems as item (item.value)}
          <option value={item.value}>{item.label}</option>
        {/each}
      </select>
    </div>
  {:else if field.field_type === "parent_child_link" && field.child_entity}
    <select
      bind:value
      {disabled}
      required={field.required}
      class="w-full h-8 rounded-none border border-input bg-transparent px-2.5 py-1 text-xs outline-none focus-visible:ring-1 disabled:cursor-not-allowed disabled:opacity-50"
    >
      <option value="">Select {field.label.toLowerCase()}</option>
      {#each parentChildItems as item (item.value)}
        <option value={item.value}>{item.label}</option>
      {/each}
    </select>
  {:else if field.field_type === "query_link" && field.query?.key}
    <div class="flex items-center gap-2">
      <select
        bind:value
        {disabled}
        required={field.required}
        class="flex-1 w-full h-8 rounded-none border border-input bg-transparent px-2.5 py-1 text-xs outline-none focus-visible:ring-1 disabled:cursor-not-allowed disabled:opacity-50"
      >
        <option value="">Select {field.label.toLowerCase()}</option>
        {#each queryLinkItems as item (item.value)}
          <option value={item.value}>{item.label}</option>
        {/each}
      </select>
    </div>
  {:else}
    <Input
      bind:value
      {placeholder}
      required={field.required}
      {disabled}
      class="w-full"
    />
  {/if}
</div>
