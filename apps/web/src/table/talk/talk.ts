// SPDX-License-Identifier: Apache-2.0
// `room.talk`: what the agents said to each other, read without ever throwing. A missing or
// malformed value becomes an empty talk, so the table still draws.

export const INTENTS = ["ask", "answer", "trade", "caveat", "agree", "disagree"] as const;
export type Intent = (typeof INTENTS)[number];

export type TalkLine = {
  seq: number;
  id: string;
  from: string;
  /** "room", or the seat the line is for. */
  to: string;
  intent: Intent;
  text: string;
  re: string | null;
  stage: "start" | "change";
};

export type Talk = {
  open: boolean;
  round: number;
  rounds: number;
  stage: "start" | "change" | null;
  waiting_for: string[];
  thread: TalkLine[];
  revised: { seat: string; needs: string[]; at: string }[];
  mine: { whisper: string | null; listening: boolean };
};

type Rec = Record<string, unknown>;
const isRec = (v: unknown): v is Rec => typeof v === "object" && v !== null && !Array.isArray(v);
const str = (v: unknown): string => (typeof v === "string" ? v : "");
const num = (v: unknown): number => (typeof v === "number" && Number.isFinite(v) ? v : 0);
const recs = (v: unknown): Rec[] => (Array.isArray(v) ? v.filter(isRec) : []);
const strs = (v: unknown): string[] =>
  Array.isArray(v) ? v.filter((x): x is string => typeof x === "string") : [];

export const EMPTY_TALK: Talk = {
  open: false,
  round: 0,
  rounds: 0,
  stage: null,
  waiting_for: [],
  thread: [],
  revised: [],
  mine: { whisper: null, listening: false },
};

export function readTalk(v: unknown): Talk {
  if (!isRec(v)) return EMPTY_TALK;
  const mine = isRec(v.mine) ? v.mine : {};
  return {
    open: v.open === true,
    round: num(v.round),
    rounds: num(v.rounds),
    stage: v.stage === "start" || v.stage === "change" ? v.stage : null,
    waiting_for: strs(v.waiting_for),
    thread: recs(v.thread)
      .filter((t) => str(t.id) !== "" && str(t.text) !== "")
      .map((t) => ({
        seq: num(t.seq),
        id: str(t.id),
        from: str(t.from),
        to: str(t.to) || "room",
        intent: (INTENTS as readonly string[]).includes(str(t.intent))
          ? (t.intent as Intent)
          : "caveat",
        text: str(t.text),
        re: str(t.re) || null,
        stage: t.stage === "change" ? "change" : "start",
      })),
    revised: recs(v.revised).map((r) => ({
      seat: str(r.seat),
      needs: strs(r.needs),
      at: str(r.at),
    })),
    mine: {
      whisper: str(mine.whisper) || null,
      listening: mine.listening === true,
    },
  };
}

/** The talk out of a viewer state: `state.room.talk`. */
export function talkOf(state: unknown): Talk {
  const room = isRec(state) && isRec(state.room) ? state.room : null;
  return readTalk(room?.talk);
}

/** Plain words for an intent, as a person would say it. */
export const INTENT_WORDS: Record<Intent, string> = {
  ask: "asks",
  answer: "answers",
  trade: "offers a trade",
  caveat: "warns",
  agree: "agrees",
  disagree: "disagrees",
};

/** The newest line of each seat, newest last: what the bubbles on the ring show. */
export function latestBySeat(talk: Talk, keep = 3): TalkLine[] {
  const seen = new Map<string, TalkLine>();
  for (const line of talk.thread) seen.set(line.from, line);
  return [...seen.values()].sort((a, b) => a.seq - b.seq).slice(-keep);
}

/** The lines whose beams are drawn: the newest few, so the ring never fills with lines. */
export function beamLines(talk: Talk, keep = 4): TalkLine[] {
  return talk.thread.slice(-keep);
}
