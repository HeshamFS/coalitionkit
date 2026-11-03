// SPDX-License-Identifier: Apache-2.0
// Taking a result with you: its text, a .csv for tables, a .ics for a schedule. All of it is made
// in the browser from the result's own `data`; if the data does not hold what a format needs, that
// format is not offered, and nothing is guessed.
import type { RoomResult } from "./room";

type Rec = Record<string, unknown>;
const isRec = (v: unknown): v is Rec => v !== null && typeof v === "object" && !Array.isArray(v);

/** `{value, event_ref}` numbers show as their value. */
function plain(v: unknown): unknown {
  return isRec(v) && "value" in v && "event_ref" in v ? v.value : v;
}

const KEYS = ["rows", "items", "lines", "entries", "days", "slots", "list", "events", "stands"];

/** The first list of records in the data: the data itself, a well-known key, or any key. */
export function rowsOf(data: unknown): Rec[] | null {
  const recs = (v: unknown): Rec[] | null =>
    Array.isArray(v) && v.length > 0 && v.every(isRec) ? (v as Rec[]) : null;
  const direct = recs(data);
  if (direct) return direct;
  if (!isRec(data)) return null;
  for (const k of KEYS) {
    const hit = recs(data[k]);
    if (hit) return hit;
  }
  for (const v of Object.values(data)) {
    const hit = recs(v);
    if (hit) return hit;
  }
  return null;
}

const cell = (v: unknown): string => {
  const x = plain(v);
  if (x === null || x === undefined) return "";
  return typeof x === "object" ? JSON.stringify(x) : String(x);
};

function columns(rows: Rec[]): string[] {
  const cols: string[] = [];
  for (const r of rows) for (const k of Object.keys(r)) if (!cols.includes(k)) cols.push(k);
  return cols;
}

const quote = (s: string) => (/[",\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s);

export function toCsv(rows: Rec[]): string {
  const cols = columns(rows);
  const lines = [cols.map(quote).join(",")];
  for (const r of rows) lines.push(cols.map((c) => quote(cell(r[c]))).join(","));
  return `${lines.join("\r\n")}\r\n`;
}

const TEXT_KEYS = ["text", "draft", "body", "content", "message"];

/** The result as plain text: a draft's words, a table as tab-separated lines, else the data. */
export function toText(result: RoomResult): string {
  const d = result.data;
  if (typeof d === "string") return d;
  if (isRec(d)) {
    for (const k of TEXT_KEYS) if (typeof d[k] === "string" && d[k] !== "") return d[k] as string;
  }
  const rows = rowsOf(d);
  if (rows) {
    const cols = columns(rows);
    return [cols.join("\t"), ...rows.map((r) => cols.map((c) => cell(r[c])).join("\t"))].join("\n");
  }
  return d === null || d === undefined ? result.title : JSON.stringify(d, null, 2);
}

const stamp = (iso: string): string | null => {
  if (/^\d{4}-\d{2}-\d{2}$/.test(iso)) return `;VALUE=DATE:${iso.replace(/-/g, "")}`;
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return null;
  return `:${new Date(t)
    .toISOString()
    .replace(/[-:]/g, "")
    .replace(/\.\d{3}/, "")}`;
};

const ics = (s: string) => s.replace(/([,;\\])/g, "\\$1").replace(/\r?\n/g, "\\n");

/** A calendar file, only if some rows carry a start time. Otherwise null. */
export function toIcs(result: RoomResult): string | null {
  const rows = rowsOf(result.data) ?? [];
  const events: string[] = [];
  rows.forEach((r, i) => {
    const start = stamp(cell(r.start ?? r.begin ?? r.from ?? r.when));
    if (!start) return;
    const end = stamp(cell(r.end ?? r.until ?? r.to));
    const title = cell(r.title ?? r.label ?? r.name ?? r.summary) || result.title;
    events.push(
      "BEGIN:VEVENT",
      `UID:${result.id}-${i}@coalitionkit`,
      `DTSTAMP:${new Date()
        .toISOString()
        .replace(/[-:]/g, "")
        .replace(/\.\d{3}/, "")}`,
      `DTSTART${start}`,
      ...(end ? [`DTEND${end}`] : []),
      `SUMMARY:${ics(title)}`,
      "END:VEVENT",
    );
  });
  if (events.length === 0) return null;
  return `${["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//coalitionkit//table//EN", ...events, "END:VCALENDAR"].join("\r\n")}\r\n`;
}

export type Export = { label: string; file: string; mime: string; body: string };

const slug = (s: string) =>
  s
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "") || "result";

/** The downloads this result can honestly offer. */
export function exportsFor(result: RoomResult): Export[] {
  const out: Export[] = [];
  const rows = rowsOf(result.data);
  const name = slug(result.title);
  if (rows)
    out.push({ label: "Export .csv", file: `${name}.csv`, mime: "text/csv", body: toCsv(rows) });
  if (result.kind === "schedule") {
    const body = toIcs(result);
    if (body) out.push({ label: "Export .ics", file: `${name}.ics`, mime: "text/calendar", body });
  }
  return out;
}

export function download(x: Export): void {
  const url = URL.createObjectURL(new Blob([x.body], { type: `${x.mime};charset=utf-8` }));
  const a = document.createElement("a");
  a.href = url;
  a.download = x.file;
  document.body.append(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
