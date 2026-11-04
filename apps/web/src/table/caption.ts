// SPDX-License-Identifier: Apache-2.0
// The line under the band: what the room is doing, taken from the host's own activity labels.
// With nothing running and nothing new, it says where the room stands, never that work is going on.
import { elapsed } from "./phase";
import type { Activity, Room } from "./room";

export type Caption = { text: string; sub: string };

const SOURCE = { model: "Model", rules: "Rules", host: "Host" } as const;

export function subOf(a: Activity): string {
  const how =
    a.state === "running"
      ? "running"
      : a.state === "failed"
        ? "failed, the rules took over"
        : a.ms === null
          ? "done"
          : `done in ${elapsed(a.ms)}`;
  return `${SOURCE[a.source]} · ${how}`;
}

/** Newest first by their own time; entries without a time keep the host's order (later is newer). */
export function newest(list: Activity[]): Activity[] {
  return list
    .map((a, i) => ({ a, i }))
    .sort((x, y) => (y.a.at > x.a.at ? 1 : y.a.at < x.a.at ? -1 : y.i - x.i))
    .map((x) => x.a);
}

/** "Making Find a place" reads badly; say what is being worked on. */
export const plainLabel = (a: Activity): string =>
  a.verb === "making" ? a.label.replace(/^making\s+/i, "Working on: ") : a.label;

/** What the room is doing when nothing is running: where it stands and what it waits for. */
function resting(room: Room, ctx: { plans: number; waiting: boolean }): Caption {
  const open = room.seats.filter((s) => s.kind === "open").length;
  const people = room.seats.filter((s) => s.kind !== "open");
  const unsigned = people.filter((s) => !s.signed).length;
  const mineOpen = room.mine.brief.some((b) => b.status === "open");
  const undone = room.needs.some((n) => n.result === null);
  switch (room.phase) {
    case "gather":
      return {
        text:
          unsigned + open === 0
            ? "Everyone is seated."
            : unsigned > 0
              ? `Waiting for ${unsigned} ${unsigned === 1 ? "person" : "people"} to say yes.`
              : `${open} ${open === 1 ? "seat is" : "seats are"} still open.`,
        sub: `${people.length - unsigned} of ${people.length} signed`,
      };
    case "brief":
      return {
        text: mineOpen
          ? "Your agent has questions for you."
          : "Waiting for the others to answer their agents.",
        sub: "Answers stay private",
      };
    case "work":
      return {
        text: "The agents are comparing what each person can offer.",
        sub: "Nothing is asked of you now",
      };
    case "decide":
      return {
        text:
          ctx.plans === 0
            ? "The plans are not ready yet."
            : ctx.waiting
              ? `${ctx.plans} ${ctx.plans === 1 ? "plan" : "plans"} to choose from. It is your call.`
              : "Waiting for the others to choose.",
        sub: "Each person sees what a plan means for them",
      };
    case "commit":
      return {
        text: ctx.waiting ? "Your yes is waiting." : "Waiting for the others to say yes.",
        sub: "Agents never commit anyone",
      };
    case "ended":
      return { text: "The room is gone. What it made stays.", sub: "Results live in this tab" };
    default:
      return {
        text: undone
          ? "The agents are making things."
          : "Everything is made. Your part is on your side.",
        sub: "Each result is checked before it reaches you",
      };
  }
}

/** A change shows only while what it moved is still being re-planned. */
const changeOpen = (room: Room) =>
  room.change !== null &&
  room.phase !== "ended" &&
  room.needs.some((n) => room.change?.moved.includes(n.id) && n.result === null);

export function captionFor(room: Room, ctx: { plans: number; waiting: boolean }): Caption {
  const running = newest(room.activity).find((a) => a.state === "running" && a.label);
  if (running) return { text: plainLabel(running), sub: subOf(running) };
  if (room.change && changeOpen(room)) {
    return {
      text: room.change.text || "Something changed.",
      sub: "Only what it touches moves",
    };
  }
  return resting(room, ctx);
}
