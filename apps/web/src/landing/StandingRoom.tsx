// SPDX-License-Identifier: Apache-2.0
// A public host keeps one room forming from a fixed sentence. The landing page shows it and its
// code, so a visitor joins it; on such a host nobody else starts rooms.
import { useEffect, useState } from "react";
import "./standing.css";

export type Standing = {
  goal: string;
  code: string;
  link: string;
  seats: number;
  filled: number;
  open: boolean;
  ends_at: string;
  minutes_left: number;
  pack: string | null;
  budget_usd: number | null;
  spent_usd: number | null;
};

export async function readStanding(
  signal?: AbortSignal,
  fetchFn: typeof fetch = (...a) => globalThis.fetch(...a),
): Promise<Standing | null> {
  const res = await fetchFn("/v1/standing", { method: "GET", signal });
  if (!res.ok) return null;
  const body = (await res.json()) as { room?: Standing | null };
  return body.room ?? null;
}

export function standingLine(room: Standing): string {
  const left = Math.max(0, Math.round(room.minutes_left));
  const seats = `${room.filled} of ${room.seats} seats`;
  if (!room.open) return `${seats} · under way, ends in ${left} min`;
  return `${seats} · ends in ${left} min`;
}

export function StandingRoom({
  onJoin,
  onFound,
}: {
  onJoin: (code: string) => void;
  onFound?: (found: boolean) => void;
}) {
  const [room, setRoom] = useState<Standing | null>(null);
  useEffect(() => {
    const ctl = new AbortController();
    const load = () =>
      readStanding(ctl.signal)
        .then((found) => {
          setRoom(found);
          onFound?.(found !== null);
        })
        .catch(() => {
          if (!ctl.signal.aborted) setRoom(null);
        });
    void load();
    const timer = setInterval(load, 15000);
    return () => {
      ctl.abort();
      clearInterval(timer);
    };
  }, [onFound]);
  if (!room) return null;
  return (
    <section className="ld-standing" aria-label="The room forming now">
      <p className="ld-standing-eyebrow">{room.open ? "Forming now" : "Under way now"}</p>
      <h2 className="ld-standing-goal">{room.goal}</h2>
      <p className="ld-standing-line">{standingLine(room)}</p>
      <div className="ld-standing-row">
        <span className="ld-standing-label">Code</span>
        <code className="ld-standing-code">{room.code}</code>
        {room.open && room.filled < room.seats ? (
          <button type="button" className="ld-standing-join" onClick={() => onJoin(room.code)}>
            Take a seat
          </button>
        ) : (
          <span className="ld-standing-wait">A new room forms when this one ends.</span>
        )}
      </div>
    </section>
  );
}
