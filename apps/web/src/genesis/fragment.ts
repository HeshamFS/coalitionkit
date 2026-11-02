// SPDX-License-Identifier: Apache-2.0
// One-time secrets that arrive in the URL fragment: the start code printed by `coalitionkit up`
// (`/#start=<code>`) and an invitation (`/join#<secret>`). Browsers never send the fragment in a
// request, so neither reaches a server log. Each is read once, kept for this tab only, and removed
// from the address at once. Viewer tokens never travel this way (feed/config.ts).

const START_KEY = "ck.start";
let memoryStart = "";

function storage(): Storage | undefined {
  try {
    return globalThis.sessionStorage;
  } catch {
    return undefined;
  }
}

function dropFragment(): void {
  const url = new URL(globalThis.location.href);
  url.hash = "";
  globalThis.history.replaceState(null, "", url.toString());
}

/** Read `#start=<code>` once, keep it for this tab, and clear it from the address. */
export function takeStartCode(): string {
  const hash = globalThis.location?.hash ?? "";
  const match = /^#start=([A-Za-z0-9_-]{16,128})$/.exec(hash);
  if (match?.[1]) {
    memoryStart = match[1];
    storage()?.setItem(START_KEY, memoryStart);
    dropFragment();
  }
  return memoryStart || storage()?.getItem(START_KEY) || "";
}

export function forgetStartCode(): void {
  memoryStart = "";
  storage()?.removeItem(START_KEY);
}

/** Read `/join#<secret>` or `/join#<room code>` once and clear it from the address. */
export function takeInvitation(): string {
  const hash = globalThis.location?.hash ?? "";
  const match = /^#([A-Za-z0-9_-]{16,256}|[A-Za-z0-9]{3}-[A-Za-z0-9]{4})$/.exec(hash);
  if (!match?.[1]) return "";
  dropFragment();
  return match[1];
}
