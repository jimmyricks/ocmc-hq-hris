<script lang="ts">
  import { toast } from "$lib/notifications";
  import { taskApi } from "$lib/task-manager/api.js";
  import type { Comment, User } from "$lib/task-manager/types.js";
  import { timeAgo } from "$lib/task-manager/utils.js";

  import * as DropdownMenu from "$lib/components/ui/dropdown-menu/index.js";

  import SendIcon from "@lucide/svelte/icons/send";
  import MessageSquareIcon from "@lucide/svelte/icons/message-square";
  import Trash2Icon from "@lucide/svelte/icons/trash-2";
  import EllipsisIcon from "@lucide/svelte/icons/ellipsis";
  import PencilIcon from "@lucide/svelte/icons/pencil";

  interface Props {
    taskId: string;
    comments?: Comment[];
    users?: User[];
    currentUser?: User | null;
  }

  let {
    taskId,
    comments = $bindable([]),
    users = [],
    currentUser = null,
  }: Props = $props();

  let commentBody = $state("");
  let commentSending = $state(false);
  let editingCommentId = $state<string | null>(null);
  let editBody = $state("");

  function userName(id: string): string {
    const user = users.find((candidate) => candidate.id === id);
    return user ? user.full_name || user.email : id;
  }

  function userInitials(id: string): string {
    return userName(id)
      .split(" ")
      .map((part) => part[0])
      .filter(Boolean)
      .slice(0, 2)
      .join("")
      .toUpperCase();
  }

  async function sendComment() {
    if (!commentBody.trim()) return;
    commentSending = true;
    try {
      const created = await taskApi.addComment(taskId, commentBody.trim());
      comments = [...comments, created];
      commentBody = "";
    } catch (err: any) {
      toast.error(err.message || "Failed to add comment");
    } finally {
      commentSending = false;
    }
  }

  async function deleteComment(commentId: string) {
    try {
      await taskApi.deleteComment(taskId, commentId);
      comments = comments.filter((comment) => comment.id !== commentId);
    } catch (err: any) {
      toast.error(err.message || "Failed to delete comment");
    }
  }

  function startEditComment(commentId: string, body: string) {
    editingCommentId = commentId;
    editBody = body;
  }

  function cancelEditComment() {
    editingCommentId = null;
    editBody = "";
  }

  async function saveEditComment(commentId: string) {
    if (!editBody.trim()) return;
    try {
      const updated = await taskApi.updateComment(
        taskId,
        commentId,
        editBody.trim(),
      );
      comments = comments.map((comment) =>
        comment.id === commentId ? updated : comment,
      );
      cancelEditComment();
    } catch (err: any) {
      toast.error(err.message || "Failed to edit comment");
    }
  }
</script>

<div class="flex flex-col gap-3">
  {#if comments.length === 0}
    <div
      class="flex flex-col items-center justify-center gap-1.5 rounded-xl border border-dashed border-base-300 py-10 text-center"
    >
      <span
        class="grid size-10 place-items-center rounded-full bg-base-200 text-base-content/50"
      >
        <MessageSquareIcon class="size-5" aria-hidden="true" />
      </span>
      <p class="text-sm font-semibold">No comments yet</p>
      <p class="text-xs text-base-content/60">
        Start the conversation with the project manager.
      </p>
    </div>
  {:else}
    <div class="comment-scroll flex flex-col">
      {#each comments as comment (comment.id)}
        {@const isOwn = comment.author_id === currentUser?.id}
        <div class="chat chat-start">
          <div class="chat-image">
            <span
              class="grid size-8 place-items-center rounded-full bg-primary/10 text-xs font-semibold text-primary"
            >
              {userInitials(comment.author_id)}
            </span>
          </div>
          <div class="chat-header items-center gap-1.5">
            <span class="text-xs font-semibold text-base-content"
              >{userName(comment.author_id)}</span
            >
            <time class="text-base-content/50"
              >{timeAgo(comment.created_at)}</time
            >
            {#if isOwn && editingCommentId !== comment.id}
              <DropdownMenu.DropdownMenu class="ml-auto">
                <DropdownMenu.DropdownMenuTrigger
                  class="grid size-5 place-items-center rounded-md text-base-content/40 hover:bg-base-200 hover:text-base-content"
                  aria-label="Comment options"
                >
                  <EllipsisIcon class="size-3.5" />
                </DropdownMenu.DropdownMenuTrigger>
                <DropdownMenu.DropdownMenuContent align="end" class="w-32">
                  <DropdownMenu.DropdownMenuItem
                    onclick={() => startEditComment(comment.id, comment.body)}
                  >
                    <PencilIcon class="size-4" />
                    Edit
                  </DropdownMenu.DropdownMenuItem>
                  <DropdownMenu.DropdownMenuItem
                    variant="destructive"
                    onclick={() => deleteComment(comment.id)}
                  >
                    <Trash2Icon class="size-4" />
                    Delete
                  </DropdownMenu.DropdownMenuItem>
                </DropdownMenu.DropdownMenuContent>
              </DropdownMenu.DropdownMenu>
            {/if}
          </div>
          {#if editingCommentId === comment.id}
            <div class="col-start-2 row-start-2 flex flex-col gap-2">
              <textarea
                class="textarea w-full resize-none border-base-300"
                rows="2"
                bind:value={editBody}></textarea>
              <div class="flex gap-2">
                <button
                  class="btn btn-primary btn-xs"
                  onclick={() => saveEditComment(comment.id)}
                  disabled={!editBody.trim()}
                >
                  Save
                </button>
                <button
                  class="btn btn-ghost btn-xs"
                  onclick={cancelEditComment}
                >
                  Cancel
                </button>
              </div>
            </div>
          {:else}
            <div class="chat-bubble text-sm whitespace-pre-wrap">
              {comment.body}
            </div>
          {/if}
        </div>
      {/each}
    </div>
  {/if}

  <div class="relative">
    <textarea
      class="textarea min-h-16 w-full resize-none border-base-300 pr-12"
      placeholder="Write a comment..."
      bind:value={commentBody}
      onkeydown={(event) => {
        if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
          event.preventDefault();
          sendComment();
        }
      }}></textarea>
    <button
      class="btn btn-primary btn-sm btn-square absolute bottom-2 right-2"
      onclick={sendComment}
      disabled={!commentBody.trim() || commentSending}
      aria-label="Send comment"
    >
      {#if commentSending}
        <span class="loading loading-spinner loading-xs"></span>
      {:else}
        <SendIcon class="size-4" />
      {/if}
    </button>
  </div>
</div>

<style>
  .comment-scroll {
    max-height: 50vh;
    overflow-y: auto;
    border-radius: 8px;
    outline: none;
  }
  .comment-scroll:focus-visible {
    outline: 3px solid color-mix(in srgb, var(--color-primary) 22%, transparent);
  }
</style>
