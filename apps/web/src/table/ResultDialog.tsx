// SPDX-License-Identifier: Apache-2.0
// A result, opened. The front is the tree the host composed, drawn through the closed catalog.
// "Show the work" turns it over: the tree itself, the events it came from with their sequence
// numbers, who made it (the model or the rules) and the check it passed. Export is per kind.
import { useEffect, useRef, useState } from "react";
import type { ViewerState } from "../feed/delta";
import { download, exportsFor, toText } from "./exports";
import type { Room, RoomResult } from "./room";
import { ComposedSurface } from "./useSurface";

export type SourceRow = { id: string; seq: number | null; type: string };
export type Shown = { result: RoomResult; byLabel: string; sources: SourceRow[] };

const record = (v: unknown): Record<string, unknown> =>
  v !== null && typeof v === "object" && !Array.isArray(v) ? (v as Record<string, unknown>) : {};

/** The events a result came from, as the viewer's state knows them. */
export function sourceRows(state: ViewerState | null, ids: string[]): SourceRow[] {
  const events = record(state?.events);
  return ids.map((id) => {
    const e = record(events[id]);
    return {
      id,
      seq: typeof e.seq === "number" ? e.seq : null,
      type: typeof e.type === "string" ? e.type.replace(/^coalition\./, "") : "event",
    };
  });
}

export function byLabelOf(room: Room, by: string): string {
  const seat = room.seats.find((s) => s.seat === by);
  if (!seat) return by || "an agent";
  if (seat.you) return "Your agent";
  return seat.kind === "helper" ? seat.label : `${seat.label}'s agent`;
}

export function shownFor(room: Room, state: ViewerState | null, result: RoomResult): Shown {
  return {
    result,
    byLabel: byLabelOf(room, result.by),
    sources: sourceRows(state, result.sources),
  };
}

function Work({ result, sources }: { result: RoomResult; sources: SourceRow[] }) {
  return (
    <div className="tb-work">
      <p>
        What the {result.source === "model" ? "model" : "rules"} chose, checked against the catalog
        on the host before it reached you. Every number points at the event it came from.
      </p>
      <h4>Source events</h4>
      {sources.length === 0 ? (
        <p className="tb-quiet">The host listed no source events for this result.</p>
      ) : (
        <ul>
          {sources.map((s) => (
            <li key={s.id}>
              {s.seq === null ? "not in your view" : `seq ${s.seq}`} · {s.type}
            </li>
          ))}
        </ul>
      )}
      <h4>Check passed</h4>
      <p>
        The component tree is valid for the closed catalog. An invalid tree would have been replaced
        by a fixed one, and this one was not.
      </p>
      <h4>Tree</h4>
      <pre>{JSON.stringify(result.tree, null, 2)}</pre>
    </div>
  );
}

export function ResultDialog({ shown, onClose }: { shown: Shown; onClose: () => void }) {
  const { result, byLabel, sources } = shown;
  const [back, setBack] = useState(false);
  const [note, setNote] = useState("");
  const box = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const before = document.activeElement as HTMLElement | null;
    box.current?.focus();
    return () => before?.focus?.();
  }, []);
  const keys = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") onClose();
    if (e.key !== "Tab" || !box.current) return;
    const items = [
      ...box.current.querySelectorAll<HTMLElement>("button:not([disabled]),a[href],input"),
    ];
    const first = items[0];
    const last = items.at(-1);
    if (e.shiftKey && document.activeElement === box.current) {
      e.preventDefault();
      last?.focus();
    } else if (e.shiftKey && document.activeElement === first) {
      e.preventDefault();
      last?.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first?.focus();
    }
  };
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(toText(result));
      setNote("Copied.");
    } catch {
      setNote("This browser would not let the page copy. Select the text instead.");
    }
  };
  const files = exportsFor(result);
  const seqs = sources.map((s) => (s.seq === null ? s.id : String(s.seq)));
  return (
    // biome-ignore lint/a11y/noStaticElementInteractions: backdrop click only; Escape and Close are the keyboard ways
    <div className="tb-overlay" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div
        className="tb-doc"
        role="dialog"
        aria-modal="true"
        aria-label={result.title}
        tabIndex={-1}
        ref={box}
        onKeyDown={keys}
      >
        <div className="tb-doc-head">
          <div>
            <h3>{result.title}</h3>
            <div className="tb-doc-meta">
              {byLabel}
              {seqs.length > 0 && ` · from seq ${seqs.join(", ")}`}
              {` · ${result.source === "model" ? "model" : "rules"}`}
            </div>
          </div>
          <button type="button" className="btn tb-quietbtn" onClick={onClose}>
            Close
          </button>
        </div>
        {result.replaced_by && (
          <p className="tb-replaced" role="note">
            Replaced by a newer result after the plan changed. This one is kept for the record.
          </p>
        )}
        {back ? (
          <Work result={result} sources={sources} />
        ) : (
          <ComposedSurface
            messages={result.messages}
            emptyText="This result has nothing to draw."
          />
        )}
        <div className="tb-row">
          <button type="button" className="btn" onClick={() => setBack(!back)}>
            {back ? "Show the result" : "Show the work"}
          </button>
          <button type="button" className="btn tb-quietbtn" onClick={copy}>
            Copy text
          </button>
          {files.map((f) => (
            <button
              key={f.file}
              type="button"
              className="btn tb-quietbtn"
              onClick={() => download(f)}
            >
              {f.label}
            </button>
          ))}
        </div>
        <p className="tb-note" role="status" aria-live="polite">
          {note}
        </p>
      </div>
    </div>
  );
}
