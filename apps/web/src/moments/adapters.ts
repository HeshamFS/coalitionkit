// SPDX-License-Identifier: Apache-2.0
import type { ViewerState } from "../feed/delta";
import { deriveParticipants, eventsOf } from "../feed/derive";
import type { Crossing, OverlapProps } from "./Overlap";
import type { RippleProps } from "./Ripple";
import type { StewardBubble, TheatreAgent, TheatreBubble, TheatreProps } from "./Theatre";

/*
 * Adapters read only what the viewer's projection holds. A field that is missing is left out of
 * the result; nothing is guessed. The match result is never read here: it does not travel in the log.
 */

type Ev = ReturnType<typeof eventsOf>[number];

const record = (v: unknown): Record<string, unknown> =>
  v !== null && typeof v === "object" && !Array.isArray(v) ? (v as Record<string, unknown>) : {};
const text = (v: unknown): string => (typeof v === "string" ? v : "");
const strings = (v: unknown): string[] =>
  Array.isArray(v) ? v.filter((x): x is string => typeof x === "string" && x !== "") : [];

const HOST_DOING: Record<string, string> = {
  "coalition.charter": "setting the charter",
  "coalition.need": "publishing a need",
  "coalition.task": "opening a task",
  "coalition.query": "asking a vault",
  "coalition.propose": "drafting a plan",
  "coalition.tension": "laying out a trade-off",
  "coalition.dissolve": "closing the coalition",
};

/** Number of the first cost figure the offer states, in the order effort, money, minutes. */
function costOf(payload: Record<string, unknown>): string {
  const cost = record(payload.cost);
  for (const key of ["effort", "money", "minutes"]) {
    const v = cost[key];
    if (typeof v === "number" && Number.isFinite(v)) return `cost ${v}`;
  }
  return "";
}

/** A short neutral line built only from fields the projection carries. */
export function summaryOf(e: Pick<Ev, "type" | "payload">): string {
  const p = e.payload;
  switch (e.type) {
    case "coalition.offer": {
      const reasons = "reason" in p || "reasons" in p ? "" : "no reasons";
      return ["offer", costOf(p), reasons].filter(Boolean).join(" · ");
    }
    case "coalition.answer": {
      const r = p.result;
      return `vault answer · ${typeof r === "string" || typeof r === "number" ? r : "sent"}`;
    }
    case "coalition.match": {
      const round = text(p.round);
      return round === "request"
        ? "match · blinded points sent"
        : round === "response"
          ? "match · blinded points returned"
          : "match · exchange set up";
    }
    case "coalition.commit":
      return `commit · ${text(p.status) || "recorded"}`;
    case "coalition.ripple":
      return `ripple · invalidates ${strings(p.invalidates).length}`;
    case "coalition.observe":
      return `observation · ${text(p.source) || "edge"}`;
    default:
      return e.type.replace("coalition.", "");
  }
}

const AGENT_TYPES = new Set([
  "coalition.offer",
  "coalition.answer",
  "coalition.match",
  "coalition.commit",
  "coalition.ripple",
  "coalition.observe",
]);
const RECENT = 3;

export function theatreFrom(state: ViewerState | null): TheatreProps {
  const events = eventsOf(state);
  const people = deriveParticipants(state);
  const host = events.findLast((e) => HOST_DOING[e.type]);
  const agents: TheatreAgent[] = people.map((p) => {
    const bubbles: TheatreBubble[] = events
      .filter((e) => AGENT_TYPES.has(e.type) && e.on_behalf_of === p.id)
      .slice(-RECENT)
      .map((e) => ({
        seq: e.seq,
        type: e.type,
        summary: summaryOf(e),
        message: { seq: e.seq, type: e.type, payload: e.payload },
      }));
    return { id: p.id, seat: p.seat, label: p.label, vendor: p.vendor, bubbles };
  });
  const steward: StewardBubble[] = (
    Array.isArray(state?.steward_interventions) ? state.steward_interventions : []
  )
    .map(record)
    .filter((s) => text(s.policy))
    .map((s, i) => ({
      key: `${typeof s.seq === "number" ? s.seq : "s"}-${i}`,
      policy: text(s.policy),
      summary: text(s.summary) || undefined,
      message: { seq: typeof s.seq === "number" ? s.seq : 0, type: "steward.verdict", payload: s },
    }));
  return {
    gardener: { doing: (host && HOST_DOING[host.type]) || "waiting" },
    agents,
    steward,
    counts: {
      agents: people.length,
      vendors: new Set(people.map((p) => p.vendor).filter(Boolean)).size,
      decisions: events.filter((e) => ["coalition.tension", "coalition.propose"].includes(e.type))
        .length,
    },
  };
}

/** Two 32-bit FNV-1a passes over the blob text give a short fingerprint; the blob is never decoded. */
export function fingerprint(blob: string): string {
  let a = 0x811c9dc5;
  let b = 0x01000193;
  for (let i = 0; i < blob.length; i++) {
    const c = blob.charCodeAt(i);
    a = Math.imul(a ^ c, 0x01000193) >>> 0;
    b = Math.imul(b ^ c, 0x811c9dc5) >>> 0;
  }
  const hex = a.toString(16).padStart(8, "0") + b.toString(16).padStart(8, "0");
  return `${hex.slice(0, 4)}…${hex.slice(-2)}`;
}

/**
 * Crossings come from the match rounds in the viewer's scope. `extra` carries what only the
 * viewer's own device or own channel knows: their vault entries, a count, the result.
 */
export function overlapFrom(
  state: ViewerState | null,
  extra: Pick<OverlapProps, "vault" | "theirCount" | "result"> = {},
): OverlapProps {
  const viewer = text(state?.viewer);
  const crossings: Crossing[] = eventsOf(state)
    .filter((e) => e.type === "coalition.match" && text(e.payload.blob))
    .map((e) => ({
      seq: e.seq,
      round: text(e.payload.round),
      dir: viewer && e.on_behalf_of === viewer ? ("out" as const) : ("in" as const),
      fingerprint: fingerprint(text(e.payload.blob)),
    }));
  return { crossings, ...extra };
}

const idOf = (p: Record<string, unknown>) => text(p.task_id) || text(p.need_id);

export function rippleFrom(state: ViewerState | null, measuredMs?: number): RippleProps {
  const events = eventsOf(state);
  const nodes = new Map<string, { id: string; label: string; status?: string }>();
  const edges: { from: string; to: string }[] = [];
  for (const e of events.filter((x) => ["coalition.need", "coalition.task"].includes(x.type))) {
    const id = idOf(e.payload);
    if (!id) continue;
    const prev = nodes.get(id);
    nodes.set(id, {
      id,
      label: text(e.payload.title) || text(e.payload.description) || prev?.label || id,
      status: text(e.payload.status) || prev?.status || undefined,
    });
    for (const from of strings(e.payload.depends_on)) {
      if (!edges.some((x) => x.from === from && x.to === id)) edges.push({ from, to: id });
    }
  }
  const known = [...nodes.values()];
  const last = events.findLast((e) => e.type === "coalition.ripple");
  if (!last) return { nodes: known, edges: edges.filter((x) => nodes.has(x.from)), measuredMs };
  const invalidated = strings(last.payload.invalidates);
  const origin = text(last.payload.origin) || text(last.payload.task_id) || undefined;
  const hit = new Set(invalidated);
  const asked = new Set<string>();
  for (const c of events.filter((e) => e.type === "coalition.commit" && e.seq < last.seq)) {
    const who = text(c.on_behalf_of) || text(c.payload.participant);
    if (who && hit.has(text(c.payload.task_id))) asked.add(who);
  }
  const plan = events.findLast((e) => e.type === "coalition.propose" && e.seq < last.seq);
  for (const p of Array.isArray(plan?.payload.plans) ? plan.payload.plans.map(record) : []) {
    const rows = Array.isArray(p.assignments) ? p.assignments.map(record) : [];
    for (const a of rows)
      if (text(a.assignee) && hit.has(text(a.task_id))) asked.add(text(a.assignee));
  }
  return {
    nodes: known,
    edges: edges.filter((x) => nodes.has(x.from)),
    ripple: { seq: last.seq, origin, invalidated, change: text(last.payload.change) || undefined },
    peopleAsked: asked.size > 0 ? asked.size : undefined,
    measuredMs,
  };
}
