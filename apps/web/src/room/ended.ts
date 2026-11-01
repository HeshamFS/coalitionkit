// SPDX-License-Identifier: Apache-2.0
// What the browser keeps so the closing screen survives the end of the session. Ending a coalition
// revokes every token, so afterwards the room cannot be reloaded; the last event is all we have.
import { useSyncExternalStore } from "react";
import type { DissolveEvent } from "../moments/Dissolve";

const KEY = "ck.ended";

function store(): Storage | undefined {
  try {
    return globalThis.sessionStorage;
  } catch {
    return undefined;
  }
}

export function rememberEnded(event: { reason: string; skills_written: string[] }): void {
  store()?.setItem(
    KEY,
    JSON.stringify({ reason: event.reason, skills_written: event.skills_written }),
  );
}

export function readEnded(): DissolveEvent | null {
  try {
    const raw = JSON.parse(store()?.getItem(KEY) ?? "null") as Partial<DissolveEvent> | null;
    if (!raw || typeof raw.reason !== "string") return null;
    const skills = Array.isArray(raw.skills_written)
      ? raw.skills_written.filter((s): s is string => typeof s === "string")
      : [];
    return { reason: raw.reason as DissolveEvent["reason"], skills_written: skills };
  } catch {
    return null;
  }
}

export function clearEnded(): void {
  store()?.removeItem(KEY);
}

/** The owner's own end in progress. It lives outside the room because the room goes away with the token. */
export type EndRun = { token: string; reason: "completed" | "cancelled" };

let run: EndRun | null = null;
const listeners = new Set<() => void>();
export function beginEnd(next: EndRun | null): void {
  run = next;
  for (const fn of listeners) fn();
}

export function useEndRun(): EndRun | null {
  return useSyncExternalStore(
    (fn) => {
      listeners.add(fn);
      return () => listeners.delete(fn);
    },
    () => run,
  );
}
