// SPDX-License-Identifier: Apache-2.0
// The blue band: the brand, how full the table is, the goal in serif, the cost so far.

import type { ViewerState } from "../feed/delta";
import { Logo } from "../landing/marks";
import { closesLabel } from "../landing/rooms";
import type { Room } from "./room";

/** The host's cost meter as a small, real number. Nothing is shown unless it sent one. */
export function costLine(state: ViewerState | null): string | null {
  const m = state?.cost_meter;
  if (m === null || typeof m !== "object" || Array.isArray(m)) return null;
  const meter = m as Record<string, unknown>;
  const spent =
    typeof meter.spent === "number" && Number.isFinite(meter.spent) ? meter.spent : null;
  if (spent === null) return null;
  const money = `${Number(spent.toFixed(spent < 1 ? 3 : 2))}${typeof meter.currency === "string" && meter.currency ? ` ${meter.currency}` : ""}`;
  const calls =
    typeof meter.calls === "number" && Number.isFinite(meter.calls) ? meter.calls : null;
  return calls === null
    ? `cost ${money}`
    : `cost ${money} · ${calls} ${calls === 1 ? "call" : "calls"}`;
}

export function Band({
  room,
  state,
  onSignOut,
}: {
  room: Room;
  state: ViewerState | null;
  onSignOut?: () => void;
}) {
  const open = room.seats.filter((s) => s.kind === "open").length;
  const seats = room.seats.length;
  const cost = costLine(state);
  return (
    <header className="tb-band">
      <div className="tb-bandtop">
        <span className="tb-brand">
          <Logo size={26} />
          coalitionkit
        </span>
        <span className="tb-eyebrow">
          {seats === 0
            ? "Seats are being set"
            : `${seats} ${seats === 1 ? "seat" : "seats"}${open > 0 ? ` · ${open} open` : ""}${room.closes ? ` · ${closesLabel(room.closes)}` : ""}`}
        </span>
        {cost && <span className="tb-cost">{cost}</span>}
        {onSignOut && (
          <button type="button" className="tb-pill" onClick={onSignOut}>
            Sign out
          </button>
        )}
      </div>
      <h1 className="tb-sentence">{room.goal || "A goal is being written"}</h1>
    </header>
  );
}
