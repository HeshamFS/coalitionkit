// SPDX-License-Identifier: Apache-2.0
// What the Chain view needs from the feed, and the rows it draws from it.
import { type Envelope, entryHash, isStub, type LogEntry, type VerifyInput } from "./verify";

export type ChainRow = {
  seq: number;
  kind: "original" | "projection" | "stub";
  /** Short event type, or "outside your scope" for a stub. */
  type: string;
  /** Full hash of the entry (the value the next prev_hash holds). */
  hash: string;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function text(value: unknown): string | null {
  return typeof value === "string" && value !== "" ? value : null;
}

/**
 * The verify input held in the feed state, or `null` when any needed field is missing. The log
 * lives under `state.log` as `{coalition_id, host_card_url, created_at, host_key, entries,
 * receipts}`. Nothing is guessed: a missing field means the view says the log is not there yet.
 */
export function chainInputFrom(state: unknown): VerifyInput | null {
  if (!isRecord(state) || !isRecord(state.log)) return null;
  const log = state.log;
  const coalitionId = text(log.coalition_id);
  const hostCardUrl = text(log.host_card_url);
  const createdAt = text(log.created_at);
  const key = log.host_key;
  if (!coalitionId || !hostCardUrl || !createdAt || !isRecord(key)) return null;
  if (!text(key.kty) || !text(key.crv) || !text(key.x)) return null;
  if (!Array.isArray(log.entries) || !Array.isArray(log.receipts)) return null;
  if (!log.entries.every(isRecord) || !log.receipts.every(isRecord)) return null;
  return {
    coalitionId,
    hostCardUrl,
    createdAt,
    hostKey: key as VerifyInput["hostKey"],
    entries: log.entries as LogEntry[],
    receipts: log.receipts as Envelope[],
  };
}

function shortType(type: unknown): string {
  return typeof type === "string" ? type.replace(/^coalition\./, "") : "event";
}

/** One display row per entry; a projection and a stub show the hash their source carries. */
export async function chainRows(entries: LogEntry[]): Promise<ChainRow[]> {
  const rows: ChainRow[] = [];
  for (const [index, entry] of entries.entries()) {
    if (isStub(entry)) {
      rows.push({ seq: entry.seq, kind: "stub", type: "outside your scope", hash: entry.hash });
    } else if (entry.type === "coalition.projection") {
      const source = isRecord(entry.payload) ? entry.payload.source : undefined;
      const src = isRecord(source) ? source : {};
      rows.push({
        seq: typeof src.seq === "number" ? src.seq : index + 1,
        kind: "projection",
        type: shortType(src.type),
        hash: typeof src.hash === "string" ? src.hash : "",
      });
    } else {
      const seq = typeof entry.seq === "number" ? entry.seq : index + 1;
      rows.push({
        seq,
        kind: "original",
        type: shortType(entry.type),
        hash: await entryHash(entry),
      });
    }
  }
  return rows;
}

/** The first four hex digits and an ellipsis, as the board draws a hash. */
export function shortHash(hash: string): string {
  return hash ? `${hash.slice(0, 4)}…` : "…";
}
