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

export type TensionView = { options: { id: string; label: string }[]; tradeoffs: string[] };

/**
 * The options of a tension from the viewer own host-sent state, never from a composed tree.
 * Null when the state does not hold them (or holds another revision), so no answer is offered.
 */
export function tensionView(
  state: ViewerState | null,
  tensionId: string,
  revision: number,
): TensionView | null {
  const found = [...eventsOf(state)]
    .reverse()
    .find((e) => e.type === "coalition.tension" && e.payload.tension_id === tensionId);
  if (!found) return null;
  const rev = found.payload.revision;
  if (typeof rev === "number" && rev !== revision) return null;
  const raw = found.payload.options;
  if (!Array.isArray(raw)) return null;
  const options = raw
    .map((o) => o as { option_id?: unknown; summary?: unknown })
    .filter((o) => typeof o.option_id === "string" && typeof o.summary === "string")
    .map((o) => ({ id: o.option_id as string, label: o.summary as string }));
  if (options.length < 2) return null;
  const tradeoffs = Array.isArray(found.payload.tradeoffs)
    ? found.payload.tradeoffs.filter((t): t is string => typeof t === "string")
    : [];
  return { options, tradeoffs };
}
