// SPDX-License-Identifier: Apache-2.0
import type { LogEntry } from "../components/live";
import type { Plan } from "../components/plans";
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
    members: deriveParticipants(state).length,
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

const record = (v: unknown): Record<string, unknown> =>
  v !== null && typeof v === "object" && !Array.isArray(v) ? (v as Record<string, unknown>) : {};
const text = (v: unknown): string => (typeof v === "string" ? v : "");
const records = (v: unknown) => (Array.isArray(v) ? v.map(record) : []);

/** Only explicit identity links are used. The current host projection omits event authors. */
export function deriveParticipants(state: ViewerState | null) {
  const events = eventsOf(state);
  const charter = events.findLast((e) => e.type === "coalition.charter")?.payload;
  const names = records(charter?.participants);
  const joined = new Map<string, Record<string, unknown>>();
  for (const e of events.filter((e) => e.type === "coalition.join")) {
    const p = e.payload;
    const id = text(p.participant) || text(p.card_url) || `join-${e.seq}`;
    joined.set(id, p);
  }
  return [...joined].map(([id, p], index) => {
    const card = record(p.card);
    const named = names.find((n) => n.id === id || n.card_url === p.card_url);
    const item = events.findLast(
      (e) =>
        ["coalition.task", "coalition.need", "coalition.offer"].includes(e.type) &&
        [e.payload.participant, e.payload.assignee, e.payload.owner].includes(id),
    );
    return {
      id,
      seat: (index % 5) + 1,
      label: text(p.display_name) || text(named?.display_name) || `Member ${index + 1}`,
      agent: text(card.name),
      vendor: text(card.vendor),
      item: text(item?.payload.title) || text(item?.payload.description),
      status: text(item?.payload.status),
    };
  });
}

export function derivePlans(state: ViewerState | null): Plan[] {
  const plans = new Map<string, Plan>();
  const sourceIds = new Map(
    Object.entries(record(state?.events)).map(([id, raw]) => [record(raw).seq, id]),
  );
  for (const event of eventsOf(state).filter((e) => e.type === "coalition.propose")) {
    for (const p of records(event.payload.plans)) {
      const id = text(p.plan_id);
      if (!id) continue;
      plans.set(id, {
        id,
        label: text(p.title) || text(p.label) || id,
        description: text(p.description) || undefined,
        canDecide: false,
        objectives: Object.entries(record(p.objective_scores))
          .filter(([, value]) => typeof value === "number" && Number.isFinite(value))
          .map(([name, value]) => ({
            name,
            value: { value: value as number, event_ref: sourceIds.get(event.seq) ?? "" },
          })),
      });
    }
  }
  return [...plans.values()];
}

export function deriveMetrics(state: ViewerState | null) {
  const participants = deriveParticipants(state);
  const events = eventsOf(state);
  const metrics = [{ label: "Events", value: events.length }];
  const agents = participants.filter((p) => p.agent);
  const vendors = new Set(participants.map((p) => p.vendor).filter(Boolean));
  if (agents.length) metrics.push({ label: "Agents", value: agents.length });
  if (vendors.size) metrics.push({ label: "Vendors", value: vendors.size });
  const meter = record(state?.cost_meter);
  if (typeof meter.spent === "number" && Number.isFinite(meter.spent))
    metrics.push({
      label: text(meter.currency) ? `Spent (${text(meter.currency)})` : "Spent",
      value: meter.spent,
    });
  return metrics;
}

export function deriveDecisions(state: ViewerState | null) {
  return eventsOf(state)
    .filter((e) => e.type === "coalition.decide")
    .map((e) => ({
      seq: e.seq,
      subject: text(record(e.payload.subject).id),
      revision: record(e.payload.subject).revision,
      answer: e.payload.consent === true ? "yes" : e.payload.consent === false ? "no" : "",
      time: text(e.payload.decided_at),
      participant: text(e.payload.participant),
    }));
}

export function derivePrivateNotes(state: ViewerState | null) {
  return records(state?.privacy_notes).map((p) => ({
    participant: text(p.participant),
    knows: text(p.knows),
    notKnows: text(p.notKnows),
    because: text(p.because),
  }));
}

export function deriveSchedule(state: ViewerState | null) {
  return records(state?.schedule)
    .map((p) => ({
      id: text(p.task_id),
      title: text(p.title),
      time: text(p.start),
    }))
    .filter((p) => p.title);
}
