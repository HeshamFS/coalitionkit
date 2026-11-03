// SPDX-License-Identifier: Apache-2.0
// Taking a result with you. Each kind of result has one data shape (room-engine.md, "What the
// fields mean") and one export: `schedule` gives a .ics, `budget` and `list` give a .csv, `draft`
// gives its text, `place` gives none. All of it is made in the browser from the result's `data`;
// a result whose data does not hold what a format needs is not offered that format.
import type { RoomResult } from "./room";

type Rec = Record<string, unknown>;
const isRec = (v: unknown): v is Rec => v !== null && typeof v === "object" && !Array.isArray(v);

/** `{value, event_ref}` numbers show as their value. */
export function plain(v: unknown): unknown {
  return isRec(v) && "value" in v && "event_ref" in v ? v.value : v;
}

const cell = (v: unknown): string => {
  const x = plain(v);
  if (x === null || x === undefined) return "";
  return typeof x === "object" ? JSON.stringify(x) : String(x);
};

const list = (v: unknown): Rec[] => (Array.isArray(v) ? v.filter(isRec) : []);
const data = (r: RoomResult): Rec => (isRec(r.data) ? r.data : {});

const quote = (s: string) => (/[",\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s);
const csv = (head: string[], rows: string[][]) =>
  `${[head, ...rows].map((r) => r.map(quote).join(",")).join("\r\n")}\r\n`;

/**
 * The budget as a .csv: what people put in, the total, the time they offered (in minutes) and what
 * the host only suggests, each marked as such. Null when there is nothing to list.
 */
export function budgetCsv(r: RoomResult): string | null {
  const d = data(r);
  const cur = cell(d.currency);
  const lines = list(d.rows).map((x) => [
    cell(x.label),
    cell(x.amount),
    cur,
    cell(x.who),
    cell(x.provenance),
  ]);
  if (lines.length > 0 && d.total !== undefined) lines.push(["Total", cell(d.total), cur, "", ""]);
  for (const x of list(d.time)) {
    lines.push([
      `${cell(x.label)} (time offered)`,
      cell(x.amount),
      "minutes",
      "",
      cell(x.provenance),
    ]);
  }
  if (d.time_total !== undefined && list(d.time).length > 0) {
    lines.push(["Time offered in all", cell(d.time_total), "minutes", "", ""]);
  }
  for (const x of list(d.suggested)) {
    lines.push([
      `${cell(x.label)} (suggested)`,
      cell(x.amount),
      cell(x.unit) || cur,
      "",
      cell(x.provenance),
    ]);
  }
  if (lines.length === 0) return null;
  return csv(["label", "amount", "unit", "who", "provenance"], lines);
}

export function listCsv(r: RoomResult): string | null {
  const items = list(data(r).items);
  if (items.length === 0) return null;
  return csv(
    ["label", "who", "provenance"],
    items.map((x) => [cell(x.label), cell(x.who), cell(x.provenance)]),
  );
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
const now = () =>
  new Date()
    .toISOString()
    .replace(/[-:]/g, "")
    .replace(/\.\d{3}/, "");

/** A calendar file from `items`, only for those with a readable start. Otherwise null. */
export function toIcs(r: RoomResult): string | null {
  const events: string[] = [];
  list(data(r).items).forEach((x, i) => {
    const start = stamp(cell(x.start));
    if (!start) return;
    const end = stamp(cell(x.end));
    events.push(
      "BEGIN:VEVENT",
      `UID:${r.id}-${i}@coalitionkit`,
      `DTSTAMP:${now()}`,
      `DTSTART${start}`,
      ...(end ? [`DTEND${end}`] : []),
      `SUMMARY:${ics(cell(x.title) || r.title)}`,
      ...(cell(x.where) ? [`LOCATION:${ics(cell(x.where))}`] : []),
      "END:VEVENT",
    );
  });
  if (events.length === 0) return null;
  const head = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//coalitionkit//table//EN"];
  return `${[...head, ...events, "END:VCALENDAR"].join("\r\n")}\r\n`;
}

/** The result as plain text, by kind. Falls back to the data as JSON for an unknown shape. */
export function toText(r: RoomResult): string {
  const d = data(r);
  if (r.kind === "draft" && (typeof d.body === "string" || typeof d.subject === "string")) {
    return [cell(d.subject), cell(d.body)].filter(Boolean).join("\n\n");
  }
  if (r.kind === "place" && list(d.options).length) {
    const chosen = cell(d.chosen);
    return list(d.options)
      .map(
        (o) =>
          `${cell(o.name)}${cell(o.name) === chosen ? " (chosen)" : ""}: ${cell(o.why)}${cell(o.check) ? ` Check first: ${cell(o.check)}` : ""}`,
      )
      .join("\n");
  }
  if (r.kind === "schedule" && list(d.items).length) {
    return list(d.items)
      .map((x) =>
        [cell(x.title), cell(x.start), cell(x.end), cell(x.where)].filter(Boolean).join(" · "),
      )
      .join("\n");
  }
  if (r.kind === "budget" && list(d.rows).length) {
    const rows = list(d.rows).map((x) => `${cell(x.label)}\t${cell(x.amount)}`);
    if (d.total !== undefined) rows.push(`Total\t${cell(d.total)}`);
    return `${cell(d.currency) ? `${cell(d.currency)}\n` : ""}${rows.join("\n")}`;
  }
  if (r.kind === "list" && list(d.items).length) {
    return list(d.items)
      .map((x) => `${cell(x.label)}${cell(x.who) ? ` (${cell(x.who)})` : ""}`)
      .join("\n");
  }
  return r.data === null || r.data === undefined ? r.title : JSON.stringify(r.data, null, 2);
}

export type Export = { label: string; file: string; mime: string; body: string };

const slug = (s: string) =>
  s
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "") || "result";

/** The downloads this kind of result can honestly offer. */
export function exportsFor(r: RoomResult): Export[] {
  const name = slug(r.title);
  const pick: [string, string, string, string | null] | null =
    r.kind === "budget"
      ? ["Export .csv", `${name}.csv`, "text/csv", budgetCsv(r)]
      : r.kind === "list"
        ? ["Export .csv", `${name}.csv`, "text/csv", listCsv(r)]
        : r.kind === "schedule"
          ? ["Export .ics", `${name}.ics`, "text/calendar", toIcs(r)]
          : null;
  if (!pick || pick[3] === null) return [];
  return [{ label: pick[0], file: pick[1], mime: pick[2], body: pick[3] }];
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
