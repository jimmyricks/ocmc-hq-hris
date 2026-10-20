<script lang="ts">
  import { ApiError } from "$lib/api/index.js";
  import {
    sendAssistantMessage,
    type AssistantMessage,
  } from "$lib/assistant/api.js";
  import { Button } from "$lib/components/ui/button/index.js";
  import { Textarea } from "$lib/components/ui/textarea/index.js";
  import { toast } from "svelte-sonner";

  import ArrowUpIcon from "@lucide/svelte/icons/arrow-up";
  import ArrowUpRightIcon from "@lucide/svelte/icons/arrow-up-right";
  import BotIcon from "@lucide/svelte/icons/bot";
  import CalculatorIcon from "@lucide/svelte/icons/calculator";
  import FolderPlusIcon from "@lucide/svelte/icons/folder-plus";
  import ListTodoIcon from "@lucide/svelte/icons/list-todo";
  import MessageSquareTextIcon from "@lucide/svelte/icons/message-square-text";
  import PlusIcon from "@lucide/svelte/icons/plus";
  import SparklesIcon from "@lucide/svelte/icons/sparkles";
  import XIcon from "@lucide/svelte/icons/x";

  type ChatMessage = AssistantMessage & {
    id: string;
  };

  const suggestions = [
    {
      label: "Create a project",
      prompt: "Help me create a new project.",
      icon: FolderPlusIcon,
    },
    {
      label: "Create a task",
      prompt: "Help me create a task.",
      icon: ListTodoIcon,
    },
    {
      label: "Assign work",
      prompt: "Help me assign a task to a teammate.",
      icon: MessageSquareTextIcon,
    },
    {
      label: "HR calculations",
      prompt: "Help me calculate a payroll total.",
      icon: CalculatorIcon,
    },
  ];

  let open = $state(false);
  let draft = $state("");
  let sending = $state(false);
  let conversationId = $state<string>(createConversationId());
  let messageCounter = 0;
  let textareaRef = $state<HTMLTextAreaElement | null>(null);
  let threadRef = $state<HTMLDivElement | null>(null);
  let messages = $state<ChatMessage[]>([
    {
      id: "welcome",
      role: "assistant",
      content:
        "Hi. I'm your OCMC HQ assistant. I can help with project and task workflows, answer workspace questions, and run HR calculations once the assistant API is connected.",
    },
  ]);

  function createConversationId() {
    return globalThis.crypto?.randomUUID?.() ?? `chat-${Date.now()}`;
  }

  function makeMessage(
    role: AssistantMessage["role"],
    content: string,
  ): ChatMessage {
    messageCounter += 1;
    return { id: `${Date.now()}-${messageCounter}`, role, content };
  }

  function scrollToLatest() {
    requestAnimationFrame(() => {
      if (threadRef) threadRef.scrollTop = threadRef.scrollHeight;
    });
  }

  $effect(() => {
    messages.length;
    sending;
    if (open) scrollToLatest();
  });

  function choosePrompt(prompt: string) {
    draft = prompt;
    textareaRef?.focus();
  }

  function handleKeydown(event: KeyboardEvent) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void send();
    }
  }

  function startNewChat() {
    if (sending) return;
    conversationId = createConversationId();
    messageCounter = 0;
    messages = [
      {
        id: "welcome",
        role: "assistant",
        content: "New chat started. What would you like to work on?",
      },
    ];
    draft = "";
  }

  async function send() {
    const message = draft.trim();
    if (!message || sending) return;

    const history = messages
      .filter((item) => item.id !== "welcome")
      .slice(-12)
      .map(({ role, content }) => ({ role, content }));
    messages.push(makeMessage("user", message));
    draft = "";
    sending = true;

    try {
      const response = await sendAssistantMessage({
        message,
        conversation_id: conversationId,
        history,
      });
      conversationId = response.conversation_id || conversationId;
      messages.push(makeMessage("assistant", response.answer));
    } catch (error) {
      const notConfigured = error instanceof ApiError && error.status === 503;
      const copy = notConfigured
        ? "The chat interface is ready, but the assistant provider and RAG tools haven't been connected yet. Add your provider settings on the backend to enable responses."
        : "I couldn't reach the assistant service. Check that the backend is running and try again.";
      messages.push(makeMessage("assistant", copy));
      if (!notConfigured) toast.error("Assistant service unavailable");
    } finally {
      sending = false;
      scrollToLatest();
    }
  }
</script>

<div class="assistant-dock">
  <section
    id="assistant-chat-panel"
    class="assistant-panel flex flex-col gap-0 overflow-hidden border border-border bg-card text-card-foreground"
    aria-labelledby="assistant-chat-title"
    hidden={!open}
  >
    <header
      class="assistant-header border-b border-border/70 px-4 pb-3 pt-4 sm:px-5"
    >
      <div class="flex items-start gap-3">
        <div
          class="assistant-mark flex size-10 shrink-0 items-center justify-center rounded-lg"
        >
          <BotIcon class="size-5" />
        </div>
        <div class="min-w-0 flex-1">
          <div class="flex flex-wrap items-center gap-2">
            <h2
              id="assistant-chat-title"
              class="text-sm font-semibold tracking-tight"
            >
              OCMC assistant
            </h2>
            <span
              class="setup-badge rounded-md px-2 py-0.5 text-[9px] font-bold uppercase tracking-[0.12em]"
            >
              API pending
            </span>
          </div>
          <p class="mt-1 text-xs leading-relaxed text-muted-foreground">
            Your self-hosted project, task, and HR copilot.
          </p>
        </div>
        <div class="flex shrink-0 items-center gap-1">
          <Button
            variant="ghost"
            size="icon-sm"
            class="text-muted-foreground"
            aria-label="Start a new chat"
            onclick={startNewChat}
            disabled={sending}
          >
            <PlusIcon />
          </Button>
          <Button
            variant="ghost"
            size="icon-sm"
            class="text-muted-foreground"
            aria-label="Close chat"
            onclick={() => (open = false)}
          >
            <XIcon />
          </Button>
        </div>
      </div>
      <div class="mt-3 flex flex-wrap gap-1.5">
        <span class="source-chip">Projects & tasks</span>
        <span class="source-chip">HR calculations</span>
        <span class="source-chip">Workspace RAG</span>
      </div>
    </header>

    <div
      bind:this={threadRef}
      class="assistant-thread flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto px-4 py-4 sm:px-5"
    >
      {#each messages as message (message.id)}
        <div
          class="message-row flex gap-2.5"
          class:user-message={message.role === "user"}
        >
          {#if message.role === "assistant"}
            <span
              class="message-avatar assistant-avatar mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-full"
            >
              <SparklesIcon class="size-3.5" />
            </span>
          {/if}
          <div
            class="message-bubble max-w-[88%] rounded-lg px-3.5 py-3 text-[13px] leading-relaxed"
          >
            {message.content}
          </div>
        </div>
      {/each}

      {#if sending}
        <div class="flex items-center gap-2.5" aria-live="polite">
          <span
            class="message-avatar assistant-avatar flex size-7 items-center justify-center rounded-full"
          >
            <SparklesIcon class="size-3.5" />
          </span>
          <div
            class="flex items-center gap-1 rounded-lg border border-border/70 bg-card px-3.5 py-3"
          >
            <span class="typing-dot"></span>
            <span class="typing-dot delay-one"></span>
            <span class="typing-dot delay-two"></span>
            <span class="sr-only">Assistant is thinking</span>
          </div>
        </div>
      {/if}

      {#if messages.length === 1}
        <div class="mt-2 flex flex-col gap-2">
          <p
            class="px-1 text-[10px] font-bold uppercase tracking-[0.13em] text-muted-foreground"
          >
            Try asking
          </p>
          {#each suggestions as suggestion (suggestion.label)}
            <button
              class="suggestion-row flex items-center gap-2.5 rounded-md border border-border/70 bg-card px-3 py-2.5 text-left text-xs font-medium transition hover:border-primary/30 hover:bg-secondary/50"
              onclick={() => choosePrompt(suggestion.prompt)}
            >
              <suggestion.icon class="size-4 text-primary" />
              {suggestion.label}
              <ArrowUpRightIcon
                class="ml-auto size-3.5 text-muted-foreground"
              />
            </button>
          {/each}
        </div>
      {/if}
    </div>

    <div class="border-t border-border/70 bg-card/90 p-3 sm:p-4">
      <form
        class="composer rounded-lg border border-border/80 bg-background p-2"
        onsubmit={(event) => {
          event.preventDefault();
          void send();
        }}
      >
        <Textarea
          bind:ref={textareaRef}
          bind:value={draft}
          onkeydown={handleKeydown}
          rows={2}
          maxlength={4000}
          placeholder="Ask about work, or describe an action…"
          aria-label="Message the OCMC assistant"
          class="min-h-[58px] border-0 bg-transparent px-2 py-1 text-sm shadow-none focus-visible:border-transparent focus-visible:ring-0"
          disabled={sending}
        />
        <div class="flex items-center justify-between gap-2 px-1 pb-0.5">
          <span class="text-[10px] text-muted-foreground">
            Enter to send · Shift+Enter for a new line
          </span>
          <Button
            type="submit"
            size="icon-sm"
            class="send-button size-8 rounded-md"
            aria-label="Send message"
            disabled={!draft.trim() || sending}
          >
            <ArrowUpIcon />
          </Button>
        </div>
      </form>
      <p
        class="mt-2 text-center text-[9px] leading-relaxed text-muted-foreground"
      >
        Workspace data stays on your backend. Confirm changes before the
        assistant executes them.
      </p>
    </div>
  </section>

  <Button
    class="launcher-button h-11 gap-2 rounded-lg px-3.5 shadow-lg"
    aria-label={open ? "Close OCMC assistant" : "Open OCMC assistant"}
    aria-expanded={open}
    aria-controls="assistant-chat-panel"
    onclick={() => (open = !open)}
  >
    <span
      class="launcher-icon flex size-7 items-center justify-center rounded-md"
    >
      <SparklesIcon class="size-4" />
    </span>
    <span>{open ? "Close chat" : "Ask HQ"}</span>
  </Button>
</div>

<style>
  .assistant-dock {
    position: fixed;
    right: 1.25rem;
    bottom: 1.25rem;
    z-index: 40;
  }

  .assistant-panel {
    position: absolute;
    right: 0;
    bottom: calc(100% + 0.75rem);
    width: min(420px, calc(100vw - 2.5rem));
    height: min(640px, calc(100dvh - 6.5rem));
    min-height: min(420px, calc(100dvh - 6.5rem));
    border-radius: var(--radius);
    box-shadow: var(--shadow-float);
    animation: chat-enter 160ms ease-out;
  }

  .assistant-panel[hidden] {
    display: none;
  }

  :global(.launcher-button) {
    background: var(--primary);
    color: var(--primary-foreground);
    box-shadow: var(--shadow-float);
  }

  :global(.launcher-button:hover:not(:disabled)) {
    background: color-mix(in oklab, var(--primary) 88%, var(--pastel-rose));
  }

  .launcher-icon {
    background: color-mix(in oklab, var(--primary-foreground) 14%, transparent);
  }

  .assistant-mark {
    background: var(--pastel-pink);
    color: var(--foreground);
  }

  .setup-badge {
    background: var(--pastel-rose);
    color: var(--foreground);
  }

  .source-chip {
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 0.2rem 0.5rem;
    color: var(--muted-foreground);
    font-size: 9px;
  }

  .assistant-thread {
    background: radial-gradient(
        ellipse at 90% 0%,
        color-mix(in oklab, var(--pastel-pink) 42%, transparent),
        transparent 35%
      ),
      var(--background);
    scrollbar-width: thin;
    scrollbar-color: var(--border) transparent;
  }

  .message-row.user-message {
    justify-content: flex-end;
  }

  .message-bubble {
    white-space: pre-wrap;
    overflow-wrap: anywhere;
  }

  .assistant-avatar {
    background: var(--pastel-pink);
    color: var(--foreground);
  }

  .user-message .message-bubble {
    background: var(--primary);
    color: var(--primary-foreground);
  }

  .message-row:not(.user-message) .message-bubble {
    border: 1px solid var(--border);
    background: var(--card);
    color: var(--foreground);
    box-shadow: 0 3px 12px
      color-mix(in oklab, var(--foreground) 5%, transparent);
  }

  .suggestion-row {
    color: var(--foreground);
  }

  .composer:focus-within {
    border-color: var(--ring);
    box-shadow: 0 0 0 3px color-mix(in oklab, var(--ring) 18%, transparent);
  }

  .composer :global(.send-button) {
    background: var(--primary);
    color: var(--primary-foreground);
  }

  .composer :global(.send-button:hover:not(:disabled)) {
    background: color-mix(in oklab, var(--primary) 88%, var(--pastel-rose));
  }

  .typing-dot {
    width: 4px;
    height: 4px;
    border-radius: 50%;
    background: var(--muted-foreground);
    animation: pulse 900ms ease-in-out infinite alternate;
  }

  .delay-one {
    animation-delay: 180ms;
  }
  .delay-two {
    animation-delay: 360ms;
  }

  @keyframes pulse {
    from {
      opacity: 0.35;
      transform: translateY(1px);
    }
    to {
      opacity: 1;
      transform: translateY(-1px);
    }
  }

  @keyframes chat-enter {
    from {
      opacity: 0;
      transform: translateY(0.5rem) scale(0.985);
    }
    to {
      opacity: 1;
      transform: translateY(0) scale(1);
    }
  }

  @media (max-width: 480px) {
    .assistant-dock {
      right: 0.75rem;
      bottom: 0.75rem;
    }

    .assistant-panel {
      width: calc(100vw - 1.5rem);
      height: min(640px, calc(100dvh - 5.5rem));
      min-height: min(360px, calc(100dvh - 5.5rem));
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .typing-dot,
    .assistant-panel {
      animation: none;
    }
  }
</style>
