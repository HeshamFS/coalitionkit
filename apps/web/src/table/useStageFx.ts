// SPDX-License-Identifier: Apache-2.0
// What the stage draws, worked out from the room: where things stand, which beams, crossing, wave
// and stop are live, and what is new since the screen opened. All of it comes from the room.
import { beamsFor, busySeats, comparing } from "./beams";
import { finishedInView, useInitial, useInitialIds, useRan } from "./fresh";
import { type Layout, needPoints, ordered, type Pt, rowPoint, seatPoints } from "./geometry";
import type { Room, Stop } from "./room";

/** The newest stop that arrived while someone watched, until the room moves on past it. */
export function useCurrentStop(room: Room): Stop | null {
  const initial = useInitialIds(room.stops.map((s) => s.id));
  const latest = room.stops.at(-1);
  return latest && !initial.has(latest.id) && !room.activity.some((a) => a.at > latest.at)
    ? latest
    : null;
}

export function useStageFx(room: Room, layout: Layout) {
  const decide = room.phase === "decide";
  const ended = room.phase === "ended";
  const initialSeats = useInitialIds(room.seats.map((s) => `${s.seat}:${s.kind}`));
  const initialNeeds = useInitialIds(room.needs.map((n) => n.id));
  const initialActs = useInitialIds(room.activity.map((a) => a.id));
  const initialCommon = useInitial(room.common ? JSON.stringify(room.common) : "");
  const initialChange = useInitial(room.change ? JSON.stringify(room.change) : "");
  const ran = useRan(room.activity);
  const finished = finishedInView(room.activity, initialActs, ran);

  const centre: Pt = { x: layout.CX, y: layout.CY };
  const home = seatPoints(room.seats, layout);
  const needPts = needPoints(room.needs, layout);
  const list = ordered(room.seats);
  const where = (seat: string, i: number): Pt => {
    if (ended) return centre;
    if (decide) return rowPoint(i, list.length, layout);
    return home.get(seat) ?? centre;
  };

  const busy = busySeats(room);
  const making = new Set(
    room.activity
      .filter((a) => a.verb === "making" && a.state === "running" && a.need)
      .map((a) => a.need),
  );
  const beams = decide || ended ? [] : beamsFor(room, home, needPts, finished);
  const moved = new Set(room.change?.moved ?? []);
  const commonKey = room.common ? JSON.stringify(room.common) : "";
  const crossing = comparing(room)
    ? ("forever" as const)
    : commonKey && commonKey !== initialCommon
      ? ("once" as const)
      : null;
  const changing = room.activity.find((a) => a.verb === "changing" && a.state === "running");
  const changeKey = room.change ? JSON.stringify(room.change) : "";
  const wave = changing
    ? ("forever" as const)
    : changeKey && changeKey !== initialChange
      ? ("twice" as const)
      : null;
  const waveFrom = (room.change?.from && home.get(room.change.from)) || centre;
  // Every stop keeps its stopped beam. The newest one that arrived while someone watched is
  // "current" until the room moves on (anything newer happens); then only its beam and the badge on
  // the seat stay.
  const current = useCurrentStop(room);
  const stops = room.stops
    .filter((s) => s.seat && home.has(s.seat))
    .slice(-4)
    .map((s) => ({
      stop: s,
      from: home.get(s.seat as string) as Pt,
      toward: (s.to && home.get(s.to)) || centre,
      current: s.id === current?.id,
    }));
  return {
    centre,
    home,
    needPts,
    list,
    where,
    busy,
    making,
    beams,
    moved,
    crossing,
    wave,
    waveFrom,
    stops,
    current,
    finished,
    initialNeeds,
    initialSeats,
  };
}
