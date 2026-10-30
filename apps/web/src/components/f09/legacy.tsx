// SPDX-License-Identifier: Apache-2.0
import { useEffect, useState } from "react";
import { Icon } from "../../ui/Icon";
import { Avatar, Badge, cx, type Seat } from "../primitives";

/* ---------- ChangedValue ---------- */

export type ChangedState = "flash" | "tinted" | "seen";

/** Old value struck, new value flashes once (900 ms), stays tinted until the viewer looks. */
export function ChangedValue({
  before,
  after,
  state,
}: {
  before?: string;
  after: string;
  /** Fixed state for the gallery. Left out, the value runs flash, tinted, seen on its own. */
  state?: ChangedState;
}) {
  const [auto, setAuto] = useState<ChangedState>("flash");
  const current = state ?? auto;
  useEffect(() => {
    if (state) return;
    const timer = setTimeout(() => setAuto((s) => (s === "flash" ? "tinted" : s)), 900);
    return () => clearTimeout(timer);
  }, [state]);
  const seen = () => !state && setAuto("seen");
  return (
    // biome-ignore lint/a11y/noStaticElementInteractions: hover and focus only mark the change as seen
    <span
      aria-live="polite"
      data-state={current}
      onMouseEnter={seen}
      onFocus={seen}
      tabIndex={current === "seen" ? undefined : 0}
    >
      <span className={cx(current === "flash" && "flash", current === "tinted" && "seen")}>
        {after}
      </span>
      {before !== undefined && (
        <>
          {" "}
          <span className="mut3" style={{ textDecoration: "line-through" }}>
            <span className="sr-only">was </span>
            {before}
          </span>
        </>
      )}
    </span>
  );
}

/* ---------- RippleBanner ---------- */

export type Ripple = {
  by: string;
  change: string;
  invalidated: string[];
  untouched: string[];
};

export function RippleBanner({
  ripple,
  onOpen,
  onDismiss,
}: {
  ripple: Ripple;
  onOpen?: () => void;
  onDismiss?: () => void;
}) {
  const total = ripple.invalidated.length + ripple.untouched.length;
  return (
    <div
      className="banner bn-info"
      style={{ alignItems: "center" }}
      role="status"
      aria-live="polite"
    >
      <span className="live-dot pulse" aria-hidden="true" />
      <div className="grow">
        <b>
          {ripple.by} {ripple.change}.
        </b>{" "}
        {ripple.invalidated.length} of your {total} tasks changed; {ripple.untouched.length} stayed.
      </div>
      <button type="button" className="btn btn-sm" onClick={onOpen}>
        What changed
      </button>
      <button type="button" className="icon-btn" aria-label="Dismiss" onClick={onDismiss}>
        <Icon name="x" size="sm" />
      </button>
    </div>
  );
}

/* ---------- ActivityStream ---------- */

export type ActivityItem = {
  seq: number;
  actor: { label: string; seat: Seat };
  verb: string;
  object?: string;
  time: string;
  live?: boolean;
  aboutMe?: boolean;
  decision?: boolean;
};
type Filter = "all" | "about me" | "decisions";

export function ActivityStream({
  items,
  onOpen,
}: {
  items: ActivityItem[];
  onOpen?: (seq: number) => void;
}) {
  const [filter, setFilter] = useState<Filter>("all");
  const shown = items.filter(
    (i) => filter === "all" || (filter === "about me" ? i.aboutMe : i.decision),
  );
  return (
    <section className="col" style={{ gap: 6 }} aria-label="Activity">
      <ul className="col" style={{ gap: 0, listStyle: "none", margin: 0, padding: 0 }}>
        {shown.map((i, n) => (
          <li
            key={i.seq}
            style={{ borderBottom: n === shown.length - 1 ? undefined : "1px solid var(--line)" }}
          >
            <button
              type="button"
              className="row"
              style={{
                padding: "6px 0",
                width: "100%",
                background: "none",
                border: 0,
                textAlign: "left",
                cursor: "pointer",
                font: "inherit",
              }}
              onClick={() => onOpen?.(i.seq)}
              aria-label={`${i.actor.label} ${i.verb} ${i.object ?? ""}, ${i.time}, log entry ${i.seq}`}
            >
              {i.live ? (
                <span className="live-dot" />
              ) : (
                <Avatar seat={i.actor.seat} label={i.actor.label} size="xs" />
              )}
              <span className="small grow" style={{ color: "var(--ink)" }}>
                <b>{i.actor.label}</b> {i.verb} {i.object}
              </span>
              <span className="st">{i.time}</span>
            </button>
          </li>
        ))}
        {shown.length === 0 && <li className="small">Nothing here yet.</li>}
      </ul>
      {/* biome-ignore lint/a11y/useSemanticElements: filter chips are a labelled group */}
      <div className="row small" role="group" aria-label="Filter activity">
        {(["all", "about me", "decisions"] as const).map((f) => (
          <button
            key={f}
            type="button"
            className={cx("chip", filter === f && "chip-on")}
            style={{ height: 22, cursor: "pointer" }}
            aria-pressed={filter === f}
            onClick={() => setFilter(f)}
          >
            {f === "all" ? "All" : f === "about me" ? "About me" : "Decisions"}
          </button>
        ))}
      </div>
    </section>
  );
}

/* ---------- LogStream ---------- */

export type LogEntry = {
  seq: number;
  ts: string;
  type: string;
  summary: string;
  hash: string;
  form: "original" | "projection" | "receipt-only";
};

export function LogStream({
  entries,
  selected,
  chainOk = true,
  onOpen,
}: {
  entries: LogEntry[];
  selected?: number;
  chainOk?: boolean;
  onOpen?: (seq: number) => void;
}) {
  const rows: (LogEntry | { gap: [number, number] })[] = [];
  entries.forEach((e, i) => {
    const prev = entries[i - 1];
    if (prev && e.seq - prev.seq > 1) rows.push({ gap: [prev.seq + 1, e.seq - 1] });
    rows.push(e);
  });
  return (
    <section className="code" aria-label="Coalition log, your projection">
      <div className="code-head">
        <span>coalition log {"·"} your projection</span>
        <span className="h-right row" style={{ gap: 6 }}>
          <span className="chip" style={{ height: 20, fontSize: 10.5 }}>
            all types
          </span>
          {chainOk ? (
            <Badge kind="signed" label={"chain ✓"} />
          ) : (
            <span className="badge" style={{ background: "var(--bad-bg)", color: "var(--bad-fg)" }}>
              chain broken
            </span>
          )}
        </span>
      </div>
      <ul style={{ listStyle: "none", margin: 0, padding: 0 }}>
        {rows.map((r) => {
          if ("gap" in r) {
            return (
              <li className="ln" key={`gap-${r.gap[0]}`} style={{ color: "var(--ink-3)" }}>
                <span className="no">{"…"}</span>
                <span className="grow">
                  gap: #{r.gap[0]}
                  {r.gap[1] > r.gap[0] ? `–#${r.gap[1]}` : ""} not in your projection
                </span>
              </li>
            );
          }
          const receipt = r.form === "receipt-only";
          return (
            <li key={r.seq}>
              <button
                type="button"
                className={cx("ln", selected === r.seq && "ln-hit")}
                style={{
                  width: "100%",
                  background: selected === r.seq ? undefined : "transparent",
                  color: "inherit",
                  border: 0,
                  borderLeftWidth: 3,
                  borderLeftStyle: "solid",
                  textAlign: "left",
                  cursor: "pointer",
                  alignItems: "baseline",
                }}
                onClick={() => onOpen?.(r.seq)}
              >
                <span className="no">{r.seq}</span>
                <span style={{ width: 60, color: "var(--ink-3)" }}>{r.ts}</span>
                <span style={{ width: 150, color: receipt ? "var(--ink-3)" : "var(--blue-text)" }}>
                  {receipt ? "· not for you ·" : r.type}
                </span>
                <span className="grow" style={receipt ? { color: "var(--ink-3)" } : undefined}>
                  {selected === r.seq ? <b>{r.summary}</b> : r.summary}
                  {r.form === "projection" && (
                    <>
                      {" "}
                      <Badge kind="signed" label="projection" />
                    </>
                  )}
                </span>
                <span style={{ color: "var(--ink-3)" }}>{r.hash}</span>
              </button>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
