// SPDX-License-Identifier: Apache-2.0
import type { LogEntry } from "../components/live";
import type { Stage } from "../shell/bars";
import { STAGES } from "../shell/bars";
import type { ViewerState } from "./delta";

type Ev = { type: string; seq: number; payload: Record<string, unknown> };

/** The viewer projection is `{coalition_id, events: {event_id: {type, seq, payload}}}`. */
export function eventsOf(state: ViewerState | null): Ev[] {
  const raw = (state?.events ?? {}) as Record<string, Partial<Ev>>;
  return Object.values(raw)
    .map((e) => ({
      type: String(e.type ?? ""),
      seq: Number(e.seq ?? 0),
      payload: (e.payload ?? {}) as Record<string, unknown>,
    }))
    .sort((a, b) => a.seq - b.seq);
}

export type RoomModel = {
  title: string;
  members: number;
  stage: Stage;
  counts: { needs: number; offers: number; plans: number; log: number };
};

/**
 * Shell data from the viewer state. The host sends no stage field yet, so the stage is read from
 * which kinds of message the viewer can see; a string `stage` in the state wins when it appears.
 */
export function deriveRoom(state: ViewerState | null): RoomModel {
  const events = eventsOf(state);
  const has = (suffix: string) => events.some((e) => e.type === `coalition.${suffix}`);
  const count = (suffix: string) => events.filter((e) => e.type === `coalition.${suffix}`).length;
  const charter = [...events].reverse().find((e) => e.type === "coalition.charter");
  const goal = charter?.payload.goal;
  let stage: Stage = "Germinate";
  if (has("join")) stage = "Gather";
  if (has("need") || has("offer") || has("query")) stage = "Negotiate";
  if (has("propose") || has("tension")) stage = "Decide";
  if (has("commit")) stage = "Act";
  if (has("done")) stage = "Live";
  if (has("dissolve")) stage = "Dissolve";
  const declared = state?.stage;
  if (typeof declared === "string") {
    const match = STAGES.find((s) => s.toLowerCase() === declared.toLowerCase());
    if (match) stage = match;
  }
  return {
    title: typeof goal === "string" && goal ? goal : "Coalition",
    members: count("join"),
    stage,
    counts: {
      needs: count("need"),
      offers: count("offer"),
      plans: count("propose"),
      log: events.length,
    },
  };
}

export function logEntries(state: ViewerState | null): LogEntry[] {
  return eventsOf(state).map((e) => ({
    seq: e.seq,
    ts: "",
    type: e.type,
    summary: "",
    hash: "",
    form: "original" as const,
  }));
}

/** Label and value pairs for the fixed layout shown when no composed tree is usable. */
export function fixedFields(state: ViewerState | null): { label: string; value: string }[] {
  const room = deriveRoom(state);
  return [
    { label: "Coalition", value: room.title },
    { label: "Stage", value: room.stage },
    { label: "Members", value: String(room.members) },
    { label: "Needs", value: String(room.counts.needs) },
    { label: "Offers", value: String(room.counts.offers) },
    { label: "Plans", value: String(room.counts.plans) },
    { label: "Log entries", value: String(room.counts.log) },
  ];
}
