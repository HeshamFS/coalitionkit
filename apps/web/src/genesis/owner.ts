// SPDX-License-Identifier: Apache-2.0
// Whether this browser started the coalition it is in. Kept in sessionStorage next to the token and
// only used to decide whether to offer "End coalition"; the host still checks the token.

const KEY = "ck.owner";

function store(): Storage | undefined {
  try {
    return globalThis.sessionStorage;
  } catch {
    return undefined;
  }
}

export function markOwner(coalitionId: string): void {
  store()?.setItem(KEY, coalitionId);
}

export function isOwner(): boolean {
  return Boolean(store()?.getItem(KEY));
}

export function clearOwner(): void {
  store()?.removeItem(KEY);
}
