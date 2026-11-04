// SPDX-License-Identifier: Apache-2.0
// Which beams the stage draws. Every one comes from a real `room.activity` entry that names a seat
// and a need: running gives a beam with sparks that keep going, a finish someone watched gives one
// last spark, an old finish gives a quiet line. Nothing here keeps its own clock.

import { newest } from "./caption";
import type { Pt } from "./geometry";
import type { Activity, Room } from "./room";
import { slotLabel } from "./slots";

export type Beam = {
  key: string;
  from: Pt;
  to: Pt;
  state: "running" | "done";
  /** A finish that happened in front of the viewer: one spark, once. */
  spark: boolean;
  /** An id that only exists for this beam's newest entry, so a new entry restarts its motion. */
  id: string;
};

const MAX_BEAMS = 40;

export function beamsFor(
  room: Room,
  seats: ReadonlyMap<string, Pt>,
  needs: ReadonlyMap<string, Pt>,
  finished: ReadonlySet<string>,
): Beam[] {
  const byPair = new Map<string, Activity>();
  for (const a of newest(room.activity)) {
    if (!a.seat || !a.need || a.state === "failed" || a.verb === "stopped") continue;
    const key = `${a.seat}>${a.need}`;
    const held = byPair.get(key);
    if (!held || (held.state !== "running" && a.state === "running")) byPair.set(key, a);
  }
  const out: Beam[] = [];
  for (const [key, a] of byPair) {
    const from = seats.get(a.seat ?? "");
    const to = needs.get(a.need ?? "");
    if (!from || !to) continue;
    out.push({
      key,
      from,
      to,
      state: a.state === "running" ? "running" : "done",
      spark: a.state === "done" && finished.has(a.id),
      id: a.id,
    });
  }
  return out.slice(0, MAX_BEAMS);
}

/** Seats whose agent is working right now, so its dot circles faster. */
export function busySeats(room: Room): Set<string> {
  return new Set(
    room.activity.filter((a) => a.state === "running" && a.seat).map((a) => a.seat as string),
  );
}

/** True while the vaults are comparing: the blinded crossing keeps going only then. */
export const comparing = (room: Room) =>
  room.activity.some((a) => a.state === "running" && a.verb === "comparing");

/** The words on the crossing's result, with only the numbers the host gave. */
export function commonLine(room: Room): string | null {
  const c = room.common;
  if (!c) return null;
  const label = (id: string) => {
    const slot = room.slots.find((s) => s.id === id);
    return slot ? slotLabel(slot) : id;
  };
  const fits = c.slots.length
    ? `${c.slots.map(label).join(" and ")} fits ${c.compared === 2 ? "you both" : c.compared > 2 ? `all ${c.compared}` : "everyone"}.`
    : "No time fits everyone yet.";
  if (c.count_private === null) return fits;
  return `${fits} Your other ${c.count_private} stayed private.`;
}

/** What the change moved, in the host's own counts. */
export function changeLine(room: Room): string | null {
  const c = room.change;
  if (!c) return null;
  const tasks = c.moved.length + c.untouched;
  const asked = `${c.asked.length} ${c.asked.length === 1 ? "person" : "people"} asked again`;
  return `${c.moved.length} of ${tasks} re-planned · ${asked} · ${c.untouched} untouched`;
}
