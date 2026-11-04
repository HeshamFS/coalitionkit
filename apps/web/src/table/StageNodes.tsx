// SPDX-License-Identifier: Apache-2.0
// The things that stand on the sheet: seats with their agent dots, needs, and the goal disc.
import type { CSSProperties } from "react";
import type { Pt } from "./geometry";
import { needStatus } from "./needWords";
import { humanStatus } from "./phase";
import type { RoomNeed, RoomSeat, Stop } from "./room";

/** Seat colour: you are blue, helpers are slate, the rest take the landing's seat colours. */
export function seatColor(seat: RoomSeat, index: number): string {
  if (seat.you) return "var(--blue)";
  if (seat.kind === "helper") return "var(--seat-5)";
  return `var(--seat-${(index % 4) + 1})`;
}

function initials(seat: RoomSeat): string {
  if (seat.you) return "You";
  if (seat.kind === "open") return "";
  const words = seat.label.split(/\s+/).filter(Boolean);
  const mark = words.length > 1 ? words.map((w) => w[0]).join("") : (words[0] ?? "").slice(0, 2);
  return mark.slice(0, 2).toUpperCase();
}

const stopWords = (stops: Stop[]) =>
  `${stops.length} ${stops.length === 1 ? "message" : "messages"} stopped by the Steward: ${stops
    .map((s) => `${s.policy}${s.explain ? `, ${s.explain}` : ""}`)
    .join("; ")}`;

const aria = (seat: RoomSeat, viewing: boolean) => {
  if (seat.you) return viewing ? "Back to my side" : "Your seat";
  if (seat.kind === "open") return "Open seat";
  return `See ${seat.label}'s screen${seat.kind === "helper" ? " (an agent)" : ""}`;
};

export function SeatNode({
  seat,
  at,
  color,
  viewing,
  stops,
  fresh,
  busy,
  fold,
  onPick,
}: {
  seat: RoomSeat;
  at: Pt;
  color: string;
  viewing: boolean;
  stops: Stop[];
  fresh: boolean;
  busy: boolean;
  /** The room has ended: the seat folds into the mark. */
  fold: boolean;
  onPick: () => void;
}) {
  const open = seat.kind === "open";
  const style = {
    left: at.x,
    top: at.y,
    opacity: fold ? 0 : 1,
    "--seat": color,
  } as CSSProperties;
  return (
    <>
      <div className="tb-seat" style={style} data-kind={seat.kind} data-fresh={fresh}>
        <button
          type="button"
          className="tb-pdot"
          data-open={open}
          data-you={seat.you}
          data-viewing={viewing}
          aria-label={aria(seat, viewing)}
          aria-pressed={seat.you ? undefined : viewing}
          disabled={open}
          onClick={onPick}
        >
          {initials(seat)}
          {stops.length > 0 && (
            <i className="tb-stopbadge" role="img" aria-label={stopWords(stops)}>
              {stops.length}
            </i>
          )}
        </button>
        <span className="tb-seatname">{open ? "Open seat" : seat.label}</span>
        {seat.kind === "helper" && <span className="tb-agenttag">agent</span>}
        {stops.length > 0 && (
          <ul className="tb-stoptip" aria-label="Stopped by the Steward">
            {stops.map((s) => (
              <li key={s.id}>
                <code>{s.policy}</code>
                {s.explain && <span>{s.explain}</span>}
              </li>
            ))}
          </ul>
        )}
        <span className="tb-seatstate">{humanStatus(seat.state) || (open ? "waiting" : "")}</span>
      </div>
      {seat.kind === "person" && (
        <div className="tb-orbit" style={style} data-busy={busy} aria-hidden="true">
          <i />
        </div>
      )}
    </>
  );
}

export function NeedNode({
  need,
  index,
  at,
  compact,
  hit,
  making,
  fresh,
  hidden,
  offers,
}: {
  need: RoomNeed;
  index: number;
  at: Pt;
  compact: boolean;
  hit: boolean;
  making: boolean;
  fresh: boolean;
  hidden: boolean;
  offers: number;
}) {
  const done = need.result !== null;
  const sub = needStatus(need.status, offers, need.kind);
  const state = hit ? "hit" : done ? "done" : "idle";
  return (
    <div
      className="tb-need"
      style={{ left: at.x, top: at.y, opacity: hidden ? 0 : 1 }}
      data-state={state}
      data-compact={compact}
      data-fresh={fresh}
      title={compact ? need.title : undefined}
    >
      {making && <div className="tb-germ" aria-hidden="true" />}
      {compact ? (
        <span className="tb-need-n">{index + 1}</span>
      ) : (
        <>
          <div className="tb-need-l">{need.title}</div>
          <div className="tb-need-c">{sub}</div>
        </>
      )}
    </div>
  );
}

export function GoalDisc({ at, text, lit }: { at: Pt; text: string; lit: boolean }) {
  return (
    <div className="tb-goal" style={{ left: at.x, top: at.y }} data-lit={lit}>
      {text}
    </div>
  );
}
