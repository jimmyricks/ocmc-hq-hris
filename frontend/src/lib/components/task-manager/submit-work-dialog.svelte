<script lang="ts">
  import * as Dialog from "$lib/components/ui/dialog/index.js";
  import * as Field from "$lib/components/ui/field/index.js";
  import { Button } from "$lib/components/ui/button/index.js";
  import { Input } from "$lib/components/ui/input/index.js";
  import { Textarea } from "$lib/components/ui/textarea/index.js";
  import SendIcon from "@lucide/svelte/icons/send";
  import type { SubmissionMode } from "$lib/task-manager/types.js";

  interface Props {
    open?: boolean;
    taskTitle: string;
    submissionMode?: SubmissionMode;
    externalLink: string;
    content: string;
    notes: string;
    submitting: boolean;
    onSubmit: () => void;
  }

  let {
    open = $bindable(false),
    taskTitle,
    submissionMode = "link",
    externalLink = $bindable(""),
    content = $bindable(""),
    notes = $bindable(""),
    submitting,
    onSubmit,
  }: Props = $props();

  const canSubmit = $derived(
    submissionMode === "text"
      ? content.trim().length > 0
      : externalLink.trim().length > 0,
  );
</script>

<Dialog.Root bind:open>
  <Dialog.Content class="max-w-lg">
    <Dialog.Header>
      <Dialog.Title>Submit Work</Dialog.Title>
      <Dialog.Description>
        {taskTitle} — this transitions the task to
        <strong>For Review</strong>.
      </Dialog.Description>
    </Dialog.Header>
    <Field.FieldGroup>
      {#if submissionMode === "text"}
        <Field.Field>
          <Field.Label for="submission-content">Content *</Field.Label>
          <Textarea
            id="submission-content"
            bind:value={content}
            placeholder="Paste the completed text (e.g. article, caption)"
            class="min-h-[160px]"
          />
        </Field.Field>
      {:else}
        <Field.Field>
          <Field.Label for="external-link">External Link *</Field.Label>
          <Input
            id="external-link"
            bind:value={externalLink}
            placeholder="https://drive.google.com/..."
          />
        </Field.Field>
      {/if}
      <Field.Field>
        <Field.Label for="submit-notes">Notes</Field.Label>
        <Textarea
          id="submit-notes"
          bind:value={notes}
          placeholder="Describe what was completed"
          class="min-h-[100px]"
        />
      </Field.Field>
    </Field.FieldGroup>
    <Dialog.Footer>
      <Button variant="outline" onclick={() => (open = false)} size="md">
        Cancel
      </Button>
      <Button
        disabled={submitting || !canSubmit}
        onclick={onSubmit}
        size="md"
        class="gap-1.5"
      >
        <SendIcon class="size-4" />
        {submitting ? "Submitting..." : "Submit for Review"}
      </Button>
    </Dialog.Footer>
  </Dialog.Content>
</Dialog.Root>
