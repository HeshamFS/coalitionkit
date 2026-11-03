// SPDX-License-Identifier: Apache-2.0
// The results outlive the room. Ending a room revokes every token, so the feed closes and the room
// cannot be reloaded; what the agents made is kept in this tab (beside the remembered ending) and
// shown again on the closing screen, each with the count of events it came from.
import { useState } from "react";
import { ResultDialog, type Shown } from "./ResultDialog";
import "./table.css";
import "./stage.css";
import "./beams.css";
import "./side.css";
import "./tray.css";

export const KEPT_KEY = "ck.ended.results";

function store(): Storage | undefined {
  try {
    return globalThis.sessionStorage;
  } catch {
    return undefined;
  }
}

export function rememberResults(shown: Shown[]): void {
  if (shown.length === 0) return;
  try {
    store()?.setItem(KEPT_KEY, JSON.stringify(shown));
  } catch {
    // The tab would not keep it (full or private). The ending still shows without the results.
  }
}

const isRec = (v: unknown): v is Record<string, unknown> =>
  v !== null && typeof v === "object" && !Array.isArray(v);

export function readKept(): Shown[] {
  try {
    const raw = JSON.parse(store()?.getItem(KEPT_KEY) ?? "[]") as unknown;
    if (!Array.isArray(raw)) return [];
    return raw.filter(
      (s): s is Shown =>
        isRec(s) &&
        isRec(s.result) &&
        typeof s.result.id === "string" &&
        typeof s.result.title === "string" &&
        Array.isArray(s.result.messages) &&
        Array.isArray(s.result.sources) &&
        Array.isArray(s.sources),
    );
  } catch {
    return [];
  }
}

/** On the closing screen: what the room made, to open, copy and take away. */
export function KeptResults() {
  const [kept] = useState(readKept);
  const [open, setOpen] = useState<Shown | null>(null);
  const current = kept.filter((s) => s.result.replaced_by === null);
  if (current.length === 0) return null;
  return (
    <div className="tb tb--kept">
      <section className="tb-keptscreen" aria-label="What the room made">
        <h2>What the room made</h2>
        <ul>
          {current.map((s) => (
            <li key={s.result.id}>
              <button type="button" className="tb-linky" onClick={() => setOpen(s)}>
                {s.result.title}
              </button>
              <small>
                {s.byLabel} · from {s.result.sources.length}{" "}
                {s.result.sources.length === 1 ? "event" : "events"}
              </small>
            </li>
          ))}
        </ul>
        {open && <ResultDialog shown={open} onClose={() => setOpen(null)} />}
      </section>
    </div>
  );
}
