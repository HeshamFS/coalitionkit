// SPDX-License-Identifier: Apache-2.0
// The place in the sentence, on the same ground as the first screen's map. Rooms hold no coordinates
// yet, so the pin marks the room's place on a pattern, and the map says it isn't a street map.
import { useMemo } from "react";
import { DotMap } from "../landing/DotMap";
import { RoomMark } from "../landing/marks";
import type { Room, Spot } from "../landing/rooms";
import { storedTheme } from "../shell/theme";

const AT: Spot = { x: 52, y: 48 };

export function PlaceMap({ place, seats }: { place: string; seats: number }) {
  const room = useMemo<Room>(
    () => ({
      id: "this-room",
      goal: place,
      seats,
      filled: 1,
      closes: "",
      lat: 0,
      lon: 0,
      status: "forming",
      sample: false,
    }),
    [place, seats],
  );
  const rooms = useMemo(() => [room], [room]);
  const where = useMemo(() => [AT], []);
  return (
    <div className="fm-map">
      <DotMap rooms={rooms} where={where} theme={storedTheme()} />
      <div className="ld-pin fm-map-pin" style={{ left: `${AT.x}%`, top: `${AT.y}%` }}>
        <span className="ld-pinmark" data-forming="true">
          <RoomMark seats={seats} filled={1} />
        </span>
        <span className="ld-pinlabel">{place}</span>
      </div>
      <span className="fm-map-note">Not a street map yet</span>
    </div>
  );
}
