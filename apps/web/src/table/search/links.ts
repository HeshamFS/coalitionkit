// SPDX-License-Identifier: Apache-2.0
// Web sources as the feed carries them: a result's `links` and the room's `search` list.
// Only http(s) URLs with a host survive; anything else from the wire is dropped here.

export type WebLink = { title: string; url: string };
export type RoomSearch = {
  id: string;
  seat: string;
  need: string | null;
  query: string;
  provider: string;
  count: number;
  first: string;
  ms: number | null;
  stopped: string | null;
};

const rec = (v: unknown): Record<string, unknown> | null =>
  v !== null && typeof v === "object" && !Array.isArray(v) ? (v as Record<string, unknown>) : null;
const text = (v: unknown): string => (typeof v === "string" ? v : "");

/** The URL if it is http(s) with a host, else null. */
export function webUrl(v: unknown): string | null {
  if (typeof v !== "string") return null;
  try {
    const u = new URL(v);
    return (u.protocol === "https:" || u.protocol === "http:") && u.host ? u.href : null;
  } catch {
    return null;
  }
}

export function readLinks(v: unknown): WebLink[] {
  if (!Array.isArray(v)) return [];
  const out: WebLink[] = [];
  for (const item of v) {
    const r = rec(item);
    const url = webUrl(r?.url);
    if (r && url) out.push({ title: text(r.title) || new URL(url).host, url });
  }
  return out.slice(0, 10);
}

export function readSearches(v: unknown): RoomSearch[] {
  if (!Array.isArray(v)) return [];
  return v
    .map(rec)
    .filter((r): r is Record<string, unknown> => r !== null && text(r.id) !== "")
    .map((r) => ({
      id: text(r.id),
      seat: text(r.seat),
      need: text(r.need) || null,
      query: text(r.query),
      provider: text(r.provider),
      count: typeof r.count === "number" ? r.count : 0,
      first: text(r.first),
      ms: typeof r.ms === "number" ? r.ms : null,
      stopped: text(r.stopped) || null,
    }));
}
