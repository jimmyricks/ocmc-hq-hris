import type { Snippet } from "svelte";

export type SelectOption = {
  value: string;
  label: string;
  disabled?: boolean;
  children?: Snippet;
};

export type SelectContext = {
  readonly value: string;
  readonly open: boolean;
  readonly disabled: boolean;
  readonly options: SelectOption[];
  readonly anchor: HTMLElement | null;
  contentEl: HTMLElement | null;
  setOpen(open: boolean): void;
  toggle(): void;
  select(option: SelectOption): void;
  register(option: SelectOption): () => void;
};

export const SELECT_CONTEXT = Symbol("hq-select");
