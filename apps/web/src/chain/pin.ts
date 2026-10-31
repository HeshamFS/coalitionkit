// SPDX-License-Identifier: Apache-2.0
// The host key, pinned per coalition the first time this browser sees it. A later log signed with
// another key fails verification instead of being trusted because it arrived with the log.
// Limit: the pin starts at first sight in this browser, not at join.

const PREFIX = "ck.hostkey.";

function storage(): Storage | undefined {
  try {
    return globalThis.localStorage;
  } catch {
    return undefined;
  }
}

export type PinResult = { ok: true; firstSight: boolean } | { ok: false; detail: string };

/** Compares `x` (the Ed25519 public key) with the pinned one; pins it when none is pinned yet. */
export function checkPin(coalitionId: string, key: { x?: unknown }): PinResult {
  const x = typeof key.x === "string" ? key.x : "";
  if (!x) return { ok: false, detail: "the host key has no public value" };
  const store = storage();
  const pinned = store?.getItem(PREFIX + coalitionId);
  if (!pinned) {
    store?.setItem(PREFIX + coalitionId, x);
    return { ok: true, firstSight: true };
  }
  return pinned === x
    ? { ok: true, firstSight: false }
    : { ok: false, detail: "the host key changed since this browser first saw this coalition" };
}
