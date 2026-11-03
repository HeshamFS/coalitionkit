// SPDX-License-Identifier: Apache-2.0
// What the agents made, growing on the table: one tile per need. A tile is a skeleton while a
// `making` activity for that need is running, and a result once the host has published it.
import { useInitialIds } from "./fresh";
import { byLabelOf } from "./ResultDialog";
import type { Room, RoomResult } from "./room";

export const trayVisible = (room: Room): boolean =>
  room.results.length > 0 ||
  room.activity.some((a) => a.verb === "making" && a.state === "running") ||
  ["commit", "make", "live", "ended"].includes(room.phase);

function Ready({
  result,
  room,
  fresh,
  onOpen,
}: {
  result: RoomResult;
  room: Room;
  fresh: boolean;
  onOpen: (id: string) => void;
}) {
  const replaced = result.replaced_by !== null;
  return (
    <button
      type="button"
      className="tb-made"
      data-fresh={fresh}
      data-replaced={replaced}
      onClick={() => onOpen(result.id)}
    >
      <b>{result.title}</b>
      <span>
        {replaced ? "replaced · " : ""}
        {byLabelOf(room, result.by)}
      </span>
    </button>
  );
}

export function Tray({ room, onOpen }: { room: Room; onOpen: (id: string) => void }) {
  const initial = useInitialIds(room.results.map((r) => r.id));
  const making = new Set(
    room.activity.filter((a) => a.verb === "making" && a.state === "running").map((a) => a.need),
  );
  if (!trayVisible(room)) return null;
  const known = new Set(room.needs.map((n) => n.id));
  const orphans = room.results.filter((r) => !known.has(r.need_id));
  return (
    <fieldset className="tb-tray">
      <legend className="tb-sr">What the agents made</legend>
      {room.needs.map((need) => {
        const mine = room.results.filter((r) => r.need_id === need.id);
        const current = mine.find((r) => r.replaced_by === null);
        const old = mine.filter((r) => r.replaced_by !== null);
        return (
          <div className="tb-slot" key={need.id}>
            {current ? (
              <Ready
                result={current}
                room={room}
                fresh={!initial.has(current.id)}
                onOpen={onOpen}
              />
            ) : making.has(need.id) ? (
              <div className="tb-made" data-state="making" role="status">
                <div className="tb-germ">making</div>
                <b>{need.title}</b>
                <span>being made</span>
              </div>
            ) : (
              <div className="tb-made" data-state="wait">
                <b>{need.title}</b>
                <span>nothing yet</span>
              </div>
            )}
            {old.map((r) => (
              <Ready key={r.id} result={r} room={room} fresh={false} onOpen={onOpen} />
            ))}
          </div>
        );
      })}
      {orphans.map((r) => (
        <div className="tb-slot" key={r.id}>
          <Ready result={r} room={room} fresh={!initial.has(r.id)} onOpen={onOpen} />
        </div>
      ))}
    </fieldset>
  );
}
