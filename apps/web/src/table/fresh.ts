// SPDX-License-Identifier: Apache-2.0
// What is new since this screen opened. Motion plays only for what arrives while someone watches:
// what was already in the room when the screen opened is drawn at rest, never replayed as news.
import { useEffect, useRef } from "react";
import type { Activity } from "./room";

/** The ids present on the first render. Stable for the life of the screen. */
export function useInitialIds(ids: string[]): ReadonlySet<string> {
  const ref = useRef<Set<string> | null>(null);
  if (ref.current === null) ref.current = new Set(ids);
  return ref.current;
}

/** The first value this screen saw. */
export function useInitial<T>(value: T): T {
  const ref = useRef<{ v: T } | null>(null);
  if (ref.current === null) ref.current = { v: value };
  return ref.current.v;
}

/** Ids this screen saw running. A finish of one of these is a finish someone watched. */
export function useRan(activity: Activity[]): ReadonlySet<string> {
  const ref = useRef<Set<string>>(new Set());
  useEffect(() => {
    for (const a of activity) if (a.state === "running") ref.current.add(a.id);
  });
  return ref.current;
}

/** Entries that finished in front of the viewer: new since opening, or seen running first. */
export function finishedInView(
  activity: Activity[],
  initial: ReadonlySet<string>,
  ran: ReadonlySet<string>,
): Set<string> {
  return new Set(
    activity
      .filter((a) => a.state !== "running" && (!initial.has(a.id) || ran.has(a.id)))
      .map((a) => a.id),
  );
}
