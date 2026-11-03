// SPDX-License-Identifier: Apache-2.0
// The `Room` the host builds per viewer (docs/ux/room-engine.md, "What the feed adds") and a reader
// that never throws: a missing or malformed value becomes an empty one, so the screen still draws.
import type { ViewerState } from "../feed/delta";

export type Phase = "gather" | "brief" | "work" | "decide" | "commit" | "make" | "live" | "ended";
export type Lights = "day" | "night";
export type Source = "model" | "rules";
export type NeedKind = "place" | "schedule" | "budget" | "list" | "draft";
export type Verb =
  | "reading"
  | "asking"
  | "offering"
  | "comparing"
  | "stopped"
  | "planning"
  | "explaining"
  | "committing"
  | "making"
  | "saying"
  | "changing"
  | "ending";

export type RoomSeat = {
  seat: string;
  role: string;
  label: string;
  kind: "person" | "helper" | "open";
  you: boolean;
  signed: boolean;
  state: string;
};
export type RoomNeed = {
  id: string;
  title: string;
  kind: NeedKind;
  detail: string;
  status: string;
  offers: number;
  assignee: string | null;
  result: string | null;
  source: Source;
};
export type Activity = {
  id: string;
  at: string;
  seat: string | null;
  verb: Verb;
  need: string | null;
  label: string;
  state: "running" | "done" | "failed";
  ms: number | null;
  source: Source | "host";
  event: string | null;
};
export type RoomResult = {
  id: string;
  need_id: string;
  kind: string;
  title: string;
  by: string;
  seq: number;
  source: Source;
  sources: string[];
  /** Log positions of the sources this viewer may see: can be shorter than `sources`. */
  seqs: number[];
  tree: unknown[];
  data: unknown;
  messages: unknown[];
  replaced_by: string | null;
};
export type Stop = {
  id: string;
  at: string;
  seat: string | null;
  /** The seat the message was aimed at, or null when it was aimed at the room. */
  to: string | null;
  policy: string;
  explain: string;
};
export type Common = { slots: string[]; count_private: number | null; compared: number };
export type Change = {
  text: string;
  /** The seat that caused the change, or null when the host did. */
  from: string | null;
  moved: string[];
  asked: string[];
  untouched: number;
};
export type BriefItem = {
  id: string;
  ask: string;
  why: string;
  component: string;
  messages: unknown[];
  status: "open" | "answered" | "skipped";
};
export type MyTask = {
  task_id: string;
  title: string;
  status: string;
  result: string | null;
  can_mark_done: boolean;
};
export type Room = {
  phase: Phase;
  lights: Lights;
  goal: string;
  /** When the room ends by itself (ISO), or null when the host did not say. */
  closes: string | null;
  seats: RoomSeat[];
  needs: RoomNeed[];
  activity: Activity[];
  slots: {
    id: string;
    label: string /** ISO start, when the host gave one */;
    start: string | null;
  }[];
  common: Common | null;
  plan_notes: Record<string, { name: string; line: string; source: Source }>;
  results: RoomResult[];
  stops: Stop[];
  checked: number;
  change: Change | null;
  begin: { can: boolean; open_seats: number } | null;
  mine: {
    brief: BriefItem[];
    /** When your agent stops waiting for answers (ISO), or null. */
    brief_closes: string | null;
    /** What the viewer is asked to decide, in plain words. Null when the host sent none. */
    asks: { kind: string; id: string; revision: number; summary: string }[] | null;
    feed: { at: string; text: string }[];
    for_you: Record<string, string>;
    tasks: MyTask[];
  };
};

const PHASES: Phase[] = ["gather", "brief", "work", "decide", "commit", "make", "live", "ended"];
const NEED_KINDS: NeedKind[] = ["place", "schedule", "budget", "list", "draft"];
const VERBS: Verb[] = [
  "reading",
  "asking",
  "offering",
  "comparing",
  "stopped",
  "planning",
  "explaining",
  "committing",
  "making",
  "saying",
  "changing",
  "ending",
];

type Rec = Record<string, unknown>;
const isRec = (v: unknown): v is Rec => v !== null && typeof v === "object" && !Array.isArray(v);
const str = (v: unknown, or = ""): string => (typeof v === "string" ? v : or);
const strOrNull = (v: unknown): string | null => (typeof v === "string" && v !== "" ? v : null);
const num = (v: unknown, or = 0): number => (typeof v === "number" && Number.isFinite(v) ? v : or);
const numOrNull = (v: unknown): number | null =>
  typeof v === "number" && Number.isFinite(v) ? v : null;
const list = (v: unknown): Rec[] => (Array.isArray(v) ? v.filter(isRec) : []);
const strings = (v: unknown): string[] =>
  Array.isArray(v) ? v.filter((x): x is string => typeof x === "string") : [];
const oneOf = <T extends string>(v: unknown, all: readonly T[], or: T): T =>
  all.includes(v as T) ? (v as T) : or;
const source = (v: unknown): Source => (v === "model" ? "model" : "rules");

function readSeats(v: unknown): RoomSeat[] {
  return list(v)
    .filter((s) => str(s.seat) !== "")
    .map((s) => ({
      seat: str(s.seat),
      role: str(s.role),
      label: str(s.label) || str(s.seat),
      kind: oneOf(s.kind, ["person", "helper", "open"] as const, "person"),
      you: s.you === true,
      signed: s.signed === true,
      state: str(s.state),
    }));
}

function readNeeds(v: unknown): RoomNeed[] {
  return list(v)
    .filter((n) => str(n.id) !== "")
    .map((n) => ({
      id: str(n.id),
      title: str(n.title) || "A need",
      kind: oneOf(n.kind, NEED_KINDS, "draft"),
      detail: str(n.detail),
      status: str(n.status),
      offers: Math.max(0, Math.trunc(num(n.offers))),
      assignee: strOrNull(n.assignee),
      result: strOrNull(n.result),
      source: source(n.source),
    }));
}

function readActivity(v: unknown): Activity[] {
  return list(v)
    .filter((a) => str(a.id) !== "")
    .map((a) => ({
      id: str(a.id),
      at: str(a.at),
      seat: strOrNull(a.seat),
      verb: oneOf(a.verb, VERBS, "reading"),
      need: strOrNull(a.need),
      label: str(a.label),
      state: oneOf(a.state, ["running", "done", "failed"] as const, "done"),
      ms: numOrNull(a.ms),
      source: a.source === "host" ? "host" : source(a.source),
      event: strOrNull(a.event),
    }));
}

function readResults(v: unknown): RoomResult[] {
  return list(v)
    .filter((r) => str(r.id) !== "")
    .map((r) => ({
      id: str(r.id),
      need_id: str(r.need_id),
      kind: str(r.kind),
      title: str(r.title) || "Result",
      by: str(r.by),
      seq: num(r.seq),
      source: source(r.source),
      sources: strings(r.sources),
      seqs: Array.isArray(r.seqs)
        ? r.seqs.filter((n): n is number => typeof n === "number" && Number.isFinite(n))
        : [],
      tree: Array.isArray(r.tree) ? r.tree : [],
      data: r.data ?? null,
      messages: Array.isArray(r.messages) ? r.messages : [],
      replaced_by: strOrNull(r.replaced_by),
    }));
}

function readCommon(v: unknown): Common | null {
  if (!isRec(v)) return null;
  return {
    slots: strings(v.slots),
    count_private: numOrNull(v.count_private),
    compared: Math.max(0, Math.trunc(num(v.compared))),
  };
}

function readChange(v: unknown): Change | null {
  if (!isRec(v)) return null;
  return {
    text: str(v.text),
    from: strOrNull(v.from),
    moved: strings(v.moved),
    asked: strings(v.asked),
    untouched: Math.max(0, Math.trunc(num(v.untouched))),
  };
}

function readNotes(v: unknown): Room["plan_notes"] {
  const out: Room["plan_notes"] = {};
  if (!isRec(v)) return out;
  for (const [id, n] of Object.entries(v)) {
    if (isRec(n)) out[id] = { name: str(n.name), line: str(n.line), source: source(n.source) };
  }
  return out;
}

function readMine(v: unknown): Room["mine"] {
  const m = isRec(v) ? v : {};
  const forYou: Record<string, string> = {};
  if (isRec(m.for_you)) {
    for (const [id, line] of Object.entries(m.for_you))
      if (typeof line === "string") forYou[id] = line;
  }
  return {
    brief: list(m.brief)
      .filter((b) => str(b.id) !== "")
      .map((b) => ({
        id: str(b.id),
        ask: str(b.ask),
        why: str(b.why),
        component: str(b.component),
        messages: Array.isArray(b.messages) ? b.messages : [],
        status: oneOf(b.status, ["open", "answered", "skipped"] as const, "open"),
      })),
    brief_closes: strOrNull(m.brief_closes),
    asks: Array.isArray(m.asks)
      ? list(m.asks)
          .filter((a) => str(a.id) !== "" && str(a.summary) !== "")
          .map((a) => ({
            kind: str(a.kind),
            id: str(a.id),
            revision: Math.trunc(num(a.revision)),
            summary: str(a.summary),
          }))
      : null,
    feed: list(m.feed).map((f) => ({ at: str(f.at), text: str(f.text) })),
    for_you: forYou,
    tasks: list(m.tasks)
      .filter((t) => str(t.task_id) !== "")
      .map((t) => ({
        task_id: str(t.task_id),
        title: str(t.title) || "A task",
        status: str(t.status),
        result: strOrNull(t.result),
        can_mark_done: t.can_mark_done === true,
      })),
  };
}

/**
 * The room in the viewer's state, or null when the host sent none (the screen then stays on the
 * five-tab room). Anything off in it is dropped or defaulted, never thrown.
 */
export function readRoom(state: ViewerState | null): Room | null {
  const raw = state?.room;
  if (!isRec(raw)) return null;
  const begin = isRec(raw.begin)
    ? {
        can: raw.begin.can === true,
        open_seats: Math.max(0, Math.trunc(num(raw.begin.open_seats))),
      }
    : null;
  return {
    phase: oneOf(raw.phase, PHASES, "gather"),
    lights: raw.lights === "night" ? "night" : "day",
    goal: str(raw.goal),
    closes: strOrNull(raw.closes),
    seats: readSeats(raw.seats),
    needs: readNeeds(raw.needs),
    activity: readActivity(raw.activity),
    slots: list(raw.slots)
      .filter((s) => str(s.id) !== "")
      .map((s) => ({
        id: str(s.id),
        label: str(s.label) || str(s.id),
        start: strOrNull(s.start),
      })),
    common: readCommon(raw.common),
    plan_notes: readNotes(raw.plan_notes),
    results: readResults(raw.results),
    stops: list(raw.stops)
      .filter((s) => str(s.id) !== "")
      .map((s) => ({
        id: str(s.id),
        at: str(s.at),
        seat: strOrNull(s.seat),
        to: strOrNull(s.to),
        policy: str(s.policy),
        explain: str(s.explain),
      })),
    checked: Math.max(0, Math.trunc(num(raw.checked))),
    change: readChange(raw.change),
    begin,
    mine: readMine(raw.mine),
  };
}

/** Light means it is your turn; night while agents work. Only the host's word decides. */
export const lightsOf = (room: Room): Lights => room.lights;
