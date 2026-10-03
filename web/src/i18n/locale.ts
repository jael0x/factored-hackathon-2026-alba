import { useSyncExternalStore } from "react";

import type { components } from "../api/schema";

export type Locale = components["schemas"]["Locale"];

// Each option is named in its own language, whatever the current one is.
export const LOCALE_NAMES: Record<Locale, string> = { es: "Español", pt: "Português" };

export const LOCALES = Object.keys(LOCALE_NAMES) as Locale[];

const DEFAULT_LOCALE: Locale = "es";

const STORAGE_KEY = "alba.locale";

const listeners = new Set<() => void>();
let locale: Locale = readStored() ?? fromBrowser(window.navigator.languages);
document.documentElement.lang = locale;

function isLocale(value: string | null): value is Locale {
  return LOCALES.some((option) => option === value);
}

function readStored(): Locale | null {
  const stored = window.localStorage.getItem(STORAGE_KEY);
  return isLocale(stored) ? stored : null;
}

function fromBrowser(languages: readonly string[]): Locale {
  for (const tag of languages) {
    const primary = tag.split("-")[0].toLowerCase();
    if (isLocale(primary)) {
      return primary;
    }
  }
  return DEFAULT_LOCALE;
}

export function setLocale(next: Locale): void {
  window.localStorage.setItem(STORAGE_KEY, next);
  locale = next;
  document.documentElement.lang = next;
  listeners.forEach((listener) => listener());
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function useLocale(): Locale {
  return useSyncExternalStore(subscribe, () => locale);
}
