<script lang="ts">
  import EntityFieldRenderer from "$lib/components/entity-field-renderer.svelte";
  import * as Field from "$lib/components/ui/field/index.js";
  import type { EntityMetaSvelte } from "$lib/components/metadata-data-table.svelte";

  interface Props {
    meta: EntityMetaSvelte;
    formData: Record<string, any>;
    disabled?: boolean;
    linkOptions?: Record<string, any[]>;
    entityName?: string;
    recordId?: string;
  }

  let {
    meta,
    formData = $bindable(),
    disabled = false,
    linkOptions = {},
    entityName,
    recordId,
  }: Props = $props();

  let fieldMap = $derived(new Map(meta.fields.map((f) => [f.key, f])));

  function isAuditField(key: string) {
    return (
      key === "id" ||
      key === "created_at" ||
      key === "updated_at" ||
      key === "created_by" ||
      key === "last_modified_by" ||
      key.startsWith("_") ||
      key.includes("audit")
    );
  }
</script>

{#if meta.field_layout?.length}
  <div class="flex flex-col gap-6">
    {#each meta.field_layout as row}
      {@const cols =
        row.length === 1 ? "grid-cols-1" : "grid-cols-1 md:grid-cols-2"}
      <Field.FieldGroup class="grid {cols} gap-4">
        {#each row as fieldName}
          {@const field = fieldMap.get(fieldName)}
          {#if field && !isAuditField(field.key) && !field.hidden}
            <Field.Field class="gap-1">
              <Field.FieldLabel>{field.title}</Field.FieldLabel>
              {#if disabled || field.readonly}
                <span class="text-sm pt-0.5">{formData[field.key] ?? "—"}</span>
              {:else}
                <EntityFieldRenderer
                  field={{
                    name: field.key,
                    label: field.title,
                    description: field.description ?? undefined,
                    field_type: field.type,
                    placeholder: field.placeholder ?? undefined,
                    required: field.required,
                    options: field.options,
                    link_entity: field.link_entity ?? undefined,
                    child_entity: field.child_entity ?? undefined,
                    parent_entity: field.parent_entity ?? undefined,
                  }}
                  bind:value={formData[field.key]}
                  {disabled}
                  {linkOptions}
                  {entityName}
                  {recordId}
                  formState={formData}
                />
              {/if}
              {#if field.description}
                <Field.FieldDescription
                  >{field.description}</Field.FieldDescription
                >
              {/if}
            </Field.Field>
          {/if}
        {/each}
      </Field.FieldGroup>
    {/each}
  </div>
{:else}
  <Field.FieldGroup class="grid grid-cols-1 md:grid-cols-2 gap-4 py-4">
    {#each meta.fields as field}
      {#if !isAuditField(field.key) && !field.hidden}
        <Field.Field class="gap-1">
          <Field.FieldLabel>{field.title}</Field.FieldLabel>
          {#if disabled || field.readonly}
            <span class="text-sm pt-0.5">{formData[field.key] ?? "—"}</span>
          {:else}
            <EntityFieldRenderer
              field={{
                name: field.key,
                label: field.title,
                description: field.description ?? undefined,
                field_type: field.type,
                placeholder: field.placeholder ?? undefined,
                required: field.required,
                options: field.options,
                link_entity: field.link_entity ?? undefined,
                child_entity: field.child_entity ?? undefined,
                parent_entity: field.parent_entity ?? undefined,
              }}
              bind:value={formData[field.key]}
              {disabled}
              {linkOptions}
              {entityName}
              {recordId}
              formState={formData}
            />
          {/if}
          {#if field.description}
            <Field.FieldDescription>{field.description}</Field.FieldDescription>
          {/if}
        </Field.Field>
      {/if}
    {/each}
  </Field.FieldGroup>
{/if}
