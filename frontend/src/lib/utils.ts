function flatten(value: unknown, output: string[]) {
  if (!value) return;
  if (typeof value === "string" || typeof value === "number" || typeof value === "bigint") {
    output.push(String(value));
    return;
  }
  if (Array.isArray(value)) {
    for (const item of value) flatten(item, output);
    return;
  }
  if (typeof value === "object") {
    for (const [key, enabled] of Object.entries(value)) {
      if (enabled) output.push(key);
    }
  }
}

export function cn(...inputs: unknown[]) {
  const output: string[] = [];
  for (const input of inputs) flatten(input, output);
  return output.join(" ");
}

export type WithoutChild<T> = T extends { child?: any } ? Omit<T, "child"> : T;
export type WithoutChildren<T> = T extends { children?: any } ? Omit<T, "children"> : T;
export type WithoutChildrenOrChild<T> = WithoutChildren<WithoutChild<T>>;
export type WithElementRef<T, U extends HTMLElement = HTMLElement> = T & {
  ref?: U | null;
};
