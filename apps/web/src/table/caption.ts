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

function standing(room: Room, plans: number): Caption {
  const open = room.seats.filter((s) => s.kind === "open").length;
  const people = room.seats.filter((s) => s.kind !== "open");
  const seated = people.filter((s) => s.signed).length;
  switch (room.phase) {
    case "gather":
      return {
        text:
          open > 0
            ? `The table is set. ${open} seat${open === 1 ? " is" : "s are"} still open.`
            : "Everyone is here.",
        sub: `${seated} of ${people.length} seated`,
      };
    case "brief":
      return {
        text: "Each agent asks its own person. Answers stay hidden.",
        sub: "Private to each seat",
      };
    case "work":
      return {
        text: "The agents work from what each person said.",
        sub: "Waiting for the host's next step",
      };
    case "decide":
      return {
        text:
          plans > 0
            ? `${plans} plan${plans === 1 ? "" : "s"}. None is best at everything.`
            : "The plans are not ready yet.",
        sub: "Each person sees what a plan means for them",
      };
    case "commit":
      return { text: "Each person says yes to their own part.", sub: "Agents never commit anyone" };
    case "ended":
      return { text: "The room is gone. What it made stays.", sub: "dissolved" };
    default:
      return {
        text: "The plan is signed. Now the agents do the work.",
        sub: "Each result is checked before it reaches you",
      };
  }
}

/** `freshDone`: ids that finished since this screen opened, so an old finish is not shown as news. */
export function captionFor(room: Room, plans: number, freshDone: ReadonlySet<string>): Caption {
  const sorted = newest(room.activity);
  const running = sorted.find((a) => a.state === "running" && a.label);
  if (running) return { text: running.label, sub: subOf(running) };
  if (room.change && room.phase !== "ended") {
    return {
      text: room.change.text || "Something changed.",
      sub: "ripple · only what it touches moves",
    };
  }
  const recent = sorted.find((a) => freshDone.has(a.id) && a.label);
  if (recent) return { text: recent.label, sub: subOf(recent) };
  return standing(room, plans);
}
