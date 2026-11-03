// SPDX-License-Identifier: Apache-2.0
// Where the room is, in words and in the order of the rail. Status only: nothing here moves the
// room forward.
import type { Phase, Room } from "./room";

export type SideKind = "gather" | "brief" | "work" | "decide" | "commit" | "live" | "ended";

/** Which panel of "your side" a phase shows. `make` is the agents making things; it reads as live. */
export function sideFor(phase: Phase): SideKind {
  return phase === "make" ? "live" : phase;
}

export const MOMENTS = [
  "Arrive",
  "Brief",
  "Agents work",
  "Decide",
  "Agents do",
  "Change",
  "Finish",
] as const;

/** The rail position of the room: the moment it is in now. Change shows only while a change is real. */
export function momentIndex(room: Pick<Room, "phase" | "change">): number {
  switch (room.phase) {
    case "gather":
      return 0;
    case "brief":
      return 1;
    case "work":
      return 2;
    case "decide":
      return 3;
    case "ended":
      return 6;
    default:
      return room.change ? 5 : 4;
  }
}

/** The one class that says the layout is the phone layout. */
export const layoutClass = (phone: boolean) => (phone ? "tb--phone" : "tb--wide");

/** "1.8 s" or "420 ms", from a measured duration. */
export function elapsed(ms: number): string {
  return ms >= 1000 ? `${(ms / 1000).toFixed(1)} s` : `${Math.round(ms)} ms`;
}

/** Plain name for a status the host sends as a code. */
export const humanStatus = (status: string): string => status.replace(/[_-]+/g, " ");
