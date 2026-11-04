// SPDX-License-Identifier: Apache-2.0
// A spark on the ring at each seat whose agent has a call running right now (`seats[].busy`),
// with the tool's name beside it. It goes out when the host records the call's finish.
import type { Pt } from "../geometry";
import type { RoomSeat } from "../room";
import "./tools.css";

export function ToolSparks({ seats, home }: { seats: RoomSeat[]; home: Map<string, Pt> }) {
  return (
    <>
      {seats.map((s) => {
        const at = home.get(s.seat);
        if (!s.busy || !at) return null;
        return (
          <div
            key={`${s.seat}:${s.busy.since}`}
            className="tk-spark"
            data-tool={s.busy.tool}
            style={{ left: at.x, top: at.y }}
          >
            <span className="tk-ring" aria-hidden="true" />
            <code className="tk-sparktag">{s.busy.tool}</code>
          </div>
        );
      })}
    </>
  );
}
