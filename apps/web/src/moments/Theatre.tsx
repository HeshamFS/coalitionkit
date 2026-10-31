// SPDX-License-Identifier: Apache-2.0
import { useState } from "react";
import "./theatre.css";

/** The real message behind a bubble, as the viewer's projection holds it. */
export type OpenMessage = { seq: number; type: string; payload: unknown };

export type TheatreBubble = { seq: number; type: string; summary: string; message: OpenMessage };
export type TheatreAgent = {
  id: string;
  /** Seat number from join order, 1 based. */
  seat: number;
  label: string;
  vendor: string;
  bubbles: TheatreBubble[];
};
export type StewardBubble = { key: string; policy: string; summary?: string; message: OpenMessage };

export type TheatreProps = {
  gardener: { doing: string };
  agents: TheatreAgent[];
  steward: StewardBubble[];
  counts: { agents: number; vendors: number; decisions: number };
};

const SEAT_COLOURS = ["#3bb3bb", "#e08a47", "#e06a9c", "#9b82e8", "#7fa3c4"];
export const seatColour = (seat: number) =>
  SEAT_COLOURS[(Math.max(1, seat) - 1) % SEAT_COLOURS.length] ?? "#3bb3bb";

/** Evenly spaced slots on an ellipse around the centre, in percent. Same input, same place. */
export function slot(index: number, total: number): { left: number; top: number } {
  const n = Math.max(1, total);
  const angle = -Math.PI / 2 + (index * 2 * Math.PI) / n + Math.PI / Math.max(2, n);
  return {
    left: Math.round((50 + 34 * Math.cos(angle)) * 10) / 10,
    top: Math.round((46 + 28 * Math.sin(angle)) * 10) / 10,
  };
}

const MARK = [
  [48.3, 15.7],
  [32, 9],
  [15.7, 15.7],
  [9, 32],
  [15.7, 48.3],
  [32, 55],
  [48.3, 48.3],
];

function Mark() {
  return (
    <svg width="44" height="44" viewBox="0 0 64 64" aria-hidden="true">
      {MARK.map(([cx, cy]) => (
        <circle key={`${cx}-${cy}`} cx={cx} cy={cy} r="5" fill="#e8edf5" />
      ))}
      <circle cx="32" cy="32" r="9" fill="#4d8dff" />
    </svg>
  );
}

function Cursor({ colour }: { colour: string }) {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true">
      <path d="M4 3l7 18 2.5-7.5L21 11z" fill={colour} />
    </svg>
  );
}

export function Theatre({ gardener, agents, steward, counts }: TheatreProps) {
  const [open, setOpen] = useState<{ title: string; message: OpenMessage } | null>(null);
  return (
    <section className="mo-theatre" aria-label="Theatre">
      <header>
        <p className="mo-t-eyebrow">Agent presence · many vendors, one table</p>
        <h3>
          Watch the agents work <em>for the people they serve.</em>
        </h3>
      </header>
      <div className="mo-t-scroll">
        <div className="mo-t-stage">
          <div className="mo-t-gardener">
            <div className="mo-t-core">
              <Mark />
            </div>
            <span className="mo-t-doing">Gardener · {gardener.doing}</span>
          </div>
          {agents.map((a, i) => {
            const at = slot(i, agents.length);
            const colour = seatColour(a.seat);
            return (
              <div
                key={a.id}
                className="mo-t-agent"
                data-drift={i % 3}
                style={{ left: `${at.left}%`, top: `${at.top}%` }}
              >
                <div className="mo-t-who">
                  <Cursor colour={colour} />
                  <span className="mo-t-tag" style={{ background: colour }}>
                    {`${a.label}'s agent · ${a.vendor || "agent"}`}
                  </span>
                </div>
                {a.bubbles.map((b, j) => (
                  <button
                    key={b.seq}
                    type="button"
                    className="mo-t-bubble"
                    data-latest={j === a.bubbles.length - 1}
                    onClick={() => setOpen({ title: `${a.label}'s agent`, message: b.message })}
                  >
                    {b.summary}
                  </button>
                ))}
              </div>
            );
          })}
          <div className="mo-t-steward">
            {steward.map((s) => (
              <button
                key={s.key}
                type="button"
                className="mo-t-bubble mo-t-red"
                onClick={() => setOpen({ title: "Steward", message: s.message })}
              >
                <b>Steward blocked</b> {s.summary ? `${s.summary} · ` : ""}policy {s.policy}
              </button>
            ))}
          </div>
        </div>
      </div>
      {open ? (
        <aside className="mo-t-panel" aria-label="Message">
          <div className="mo-t-panel-head">
            <span>
              {open.title} · seq {open.message.seq} · {open.message.type}
            </span>
            <button type="button" className="mo-t-close" onClick={() => setOpen(null)}>
              Close
            </button>
          </div>
          <pre>{JSON.stringify(open.message.payload, null, 2)}</pre>
        </aside>
      ) : null}
      <footer className="mo-t-foot">
        <span className="mo-t-count">
          <b>{counts.agents}</b> agents · <b>{counts.vendors}</b> vendors
        </span>
        <span className="mo-t-count">
          people interrupted <b>only for decisions</b> · <b>{counts.decisions}</b> asked
        </span>
        <span className="mo-t-count">every bubble opens its real message</span>
      </footer>
    </section>
  );
}
