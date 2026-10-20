import { writable } from "svelte/store";

export type Notice = {
  id: number;
  kind: "success" | "error";
  message: string;
};

export const notices = writable<Notice[]>([]);
let nextId = 1;

function notify(kind: Notice["kind"], message: string): number {
  const id = nextId++;
  notices.update((items) => [...items, { id, kind, message }]);
  setTimeout(() => dismiss(id), 4200);
  return id;
}

export function dismiss(id: number) {
  notices.update((items) => items.filter((item) => item.id !== id));
}

export const toast = {
  success: (message: string) => notify("success", message),
  error: (message: string) => notify("error", message),
};
