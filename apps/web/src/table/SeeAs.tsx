// SPDX-License-Identifier: Apache-2.0
// See the room as someone else sees it. The host composes the view for both scopes (it never
// merges them), so what comes back is only what you and they may both see. What is theirs alone
// is drawn hatched: it is there, and it is not yours.
import { useEffect, useState } from "react";
import { problemText } from "./api";
import { useTable } from "./context";
import type { RoomSeat } from "./room";
import { ComposedSurface } from "./useSurface";

type Load = { s: "loading" } | { s: "ready"; messages: unknown[] } | { s: "failed"; text: string };

export function SeeAs({ seat, onBack }: { seat: RoomSeat; onBack: () => void }) {
  const { io, room } = useTable();
  const [load, setLoad] = useState<Load>({ s: "loading" });
  const [attempt, setAttempt] = useState(0);
  // biome-ignore lint/correctness/useExhaustiveDependencies: refetch on the seat or on a retry only
  useEffect(() => {
    let live = true;
    setLoad({ s: "loading" });
    io.viewAs(seat.seat).then((r) => {
      if (!live) return;
      setLoad(
        r.ok
          ? { s: "ready", messages: Array.isArray(r.data.messages) ? r.data.messages : [] }
          : { s: "failed", text: problemText(r) },
      );
    });
    return () => {
      live = false;
    };
  }, [seat.seat, attempt]);
  const part = room.needs.filter((n) => n.assignee === seat.seat).map((n) => n.title);
  const helper = seat.kind === "helper";
  return (
    <section className="tb-viewas" aria-label={`${seat.label}'s screen`}>
      <h2>{seat.label}'s screen</h2>
      <p>
        Same room, built for {helper ? "this agent" : "them"}. You see what you both may see, and
        nothing that is only {helper ? "its owner's" : "theirs"}.
      </p>
      <div className="tb-card">
        <span className="tb-tag">{helper ? "Its part" : "Their part"}</span>
        <p>{part.length ? part.join(", ") : "No part is assigned yet."}</p>
      </div>
      <div className="tb-card">
        <span className="tb-tag">Shared between you two</span>
        {load.s === "loading" && <div className="tb-germ">composing their view</div>}
        {load.s === "failed" && (
          <>
            <p role="alert">{load.text}</p>
            <button
              type="button"
              className="btn tb-quietbtn"
              onClick={() => setAttempt(attempt + 1)}
            >
              Try again
            </button>
          </>
        )}
        {load.s === "ready" && (
          <ComposedSurface
            messages={load.messages}
            emptyText="Nothing is shared between you yet."
          />
        )}
      </div>
      {(helper
        ? ["What its owner told it"]
        : ["Their free times", "Their limits", "Their reasons"]
      ).map((label) => (
        <div className="tb-hatch" key={label}>
          {label} · private to {helper ? "its owner" : "them"}
        </div>
      ))}
      <button type="button" className="btn tb-quietbtn" onClick={onBack}>
        Back to my side
      </button>
    </section>
  );
}
