// SPDX-License-Identifier: Apache-2.0
// Light is the default for everyone, whatever the system says. Dark is a choice that this browser
// remembers. Storage can be missing or refuse, so the page works the same without it.
export type Theme = "light" | "dark";

const KEY = "ck.theme";

export function storedTheme(): Theme {
  try {
    return globalThis.localStorage?.getItem(KEY) === "dark" ? "dark" : "light";
  } catch {
    return "light";
  }
}

export function applyTheme(theme: Theme): void {
  document.documentElement.dataset.theme = theme;
}

export function applyStoredTheme(): void {
  applyTheme(storedTheme());
}

export function chooseTheme(theme: Theme): void {
  applyTheme(theme);
  try {
    globalThis.localStorage?.setItem(KEY, theme);
  } catch {
    // The choice still holds for this page.
  }
}
