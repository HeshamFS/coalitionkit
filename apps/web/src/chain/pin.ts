// SPDX-License-Identifier: Apache-2.0
// The host key, pinned per coalition when this browser joins (Genesis start or an invitation),
// from the host's join response. Verification checks the log's key against that pin. Without a
// pin (signed in with a pasted token) the result says the key was not seen at join.

const PREFIX = "ck.hostkey.";

export type PinResult = { ok: true; pinned: boolean } | { ok: false; detail: string };

/** Pins the host key at join. Returns false when the browser cannot store it. */
export function pinAtJoin(coalitionId: string, key: { x?: unknown } | undefined): boolean {
  const x = typeof key?.x === "string" ? key.x : "";
  if (!x) return false;
  try {
    globalThis.localStorage.setItem(PREFIX + coalitionId, x);
    return true;
  } catch {
    return false;
  }
}

/** Compares the log's host key with the key pinned at join. Never pins on its own. */
export function checkPin(coalitionId: string, key: { x?: unknown }): PinResult {
  const x = typeof key.x === "string" ? key.x : "";
  if (!x) return { ok: false, detail: "the host key has no public value" };
  let pinned: string | null;
  try {
    pinned = globalThis.localStorage.getItem(PREFIX + coalitionId);
  } catch {
    return { ok: false, detail: "the key pinned at join could not be read in this browser" };
  }
  if (!pinned) return { ok: true, pinned: false };
  return pinned === x
    ? { ok: true, pinned: true }
    : { ok: false, detail: "the host key differs from the one pinned when you joined" };
}
