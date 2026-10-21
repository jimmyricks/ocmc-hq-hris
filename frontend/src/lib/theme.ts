import { browser } from "$app/environment";
import { writable } from "svelte/store";

export const THEME_STORAGE_KEY = "ocmc-theme";
export const LIGHT_THEME = "hq";
export const DARK_THEME = "hq-dark";

export type Theme = typeof LIGHT_THEME | typeof DARK_THEME;

function parseTheme(value: string | null): Theme | null {
  return value === LIGHT_THEME || value === DARK_THEME ? value : null;
}

function systemTheme(): Theme {
  if (!browser) return LIGHT_THEME;
  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? DARK_THEME
    : LIGHT_THEME;
}

function storedTheme(): Theme | null {
  if (!browser) return null;
  try {
    return parseTheme(window.localStorage.getItem(THEME_STORAGE_KEY));
  } catch {
    return null;
  }
}

function initialTheme(): Theme {
  if (!browser) return LIGHT_THEME;
  return (
    storedTheme() ??
    parseTheme(document.documentElement.dataset.theme ?? null) ??
    systemTheme()
  );
}

function applyTheme(value: Theme): void {
  if (!browser) return;
  document.documentElement.dataset.theme = value;
  document.documentElement.style.colorScheme =
    value === DARK_THEME ? "dark" : "light";
}

function persistTheme(value: Theme): void {
  if (!browser) return;
  try {
    window.localStorage.setItem(THEME_STORAGE_KEY, value);
  } catch {
    return;
  }
}

export const theme = writable<Theme>(initialTheme());

theme.subscribe(applyTheme);

export function setTheme(value: Theme): void {
  persistTheme(value);
  theme.set(value);
}

export function toggleTheme(): void {
  theme.update((current) => {
    const next = current === DARK_THEME ? LIGHT_THEME : DARK_THEME;
    persistTheme(next);
    return next;
  });
}

if (browser) {
  const darkModeQuery = window.matchMedia("(prefers-color-scheme: dark)");

  darkModeQuery.addEventListener("change", (event) => {
    if (!storedTheme()) {
      theme.set(event.matches ? DARK_THEME : LIGHT_THEME);
    }
  });

  window.addEventListener("storage", (event) => {
    if (event.key !== THEME_STORAGE_KEY) return;
    theme.set(parseTheme(event.newValue) ?? systemTheme());
  });
}
