// SPDX-License-Identifier: Apache-2.0
// Where things sit on the sheet. The stage has a fixed logical size and is scaled to fit, so these
// numbers are the same on every screen. Seats stand on an outer ring that leaves the open side
// free (the landing's room mark does the same); needs stand on an inner ring around the goal.
import type { RoomNeed, RoomSeat } from "./room";

export type Layout = {
  W: number;
  H: number;
  CX: number;
  CY: number;
  RX: number;
  RY: number;
  NRX: number;
  NRY: number;
  compact: boolean;
};

export const WIDE: Layout = {
  W: 1120,
  H: 508,
  CX: 560,
  CY: 252,
  RX: 420,
  RY: 196,
  NRX: 196,
  NRY: 100,
  compact: false,
};
export const COMPACT: Layout = {
  W: 400,
  H: 452,
  CX: 200,
  CY: 214,
  RX: 148,
  RY: 188,
  NRX: 70,
  NRY: 98,
  compact: true,
};

export type Pt = { x: number; y: number };
const GAP = 46;

export const round = (n: number) => Math.round(n * 10) / 10;

const polar = (deg: number, rx: number, ry: number, l: Layout): Pt => ({
  x: round(l.CX + rx * Math.cos((-deg * Math.PI) / 180)),
  y: round(l.CY + ry * Math.sin((-deg * Math.PI) / 180)),
});

/** You sit last, at the lower right, as the others fill in around the ring. */
export function ordered(seats: RoomSeat[]): RoomSeat[] {
  return [...seats.filter((s) => !s.you), ...seats.filter((s) => s.you)];
}

export function seatPoints(seats: RoomSeat[], l: Layout): Map<string, Pt> {
  const list = ordered(seats);
  const n = list.length;
  const span = 360 - 2 * GAP;
  const out = new Map<string, Pt>();
  list.forEach((s, i) => {
    const deg = n > 1 ? GAP + (span * i) / (n - 1) : 180;
    out.set(s.seat, polar(deg, l.RX, l.RY, l));
  });
  return out;
}

export function needPoints(needs: RoomNeed[], l: Layout): Map<string, Pt> {
  const out = new Map<string, Pt>();
  needs.forEach((n, i) => {
    out.set(n.id, polar(90 + (360 / needs.length) * i, l.NRX, l.NRY, l));
  });
  return out;
}

export type BeamBox = { x: number; y: number; w: number; a: number };

export function beamBox(a: Pt, b: Pt, reach = 1): BeamBox {
  const dx = (b.x - a.x) * reach;
  const dy = (b.y - a.y) * reach;
  return {
    x: a.x,
    y: a.y,
    w: round(Math.hypot(dx, dy)),
    a: round((Math.atan2(dy, dx) * 180) / Math.PI),
  };
}

export const at = (a: Pt, b: Pt, p: number): Pt => ({
  x: round(a.x + (b.x - a.x) * p),
  y: round(a.y + (b.y - a.y) * p),
});

/** The scale that fits the stage into the room it has, never beyond 1.3. */
export function fitScale(availW: number, availH: number, l: Layout): number {
  const s = Math.min(1.3, availW / l.W, availH / l.H);
  return Math.max(0.2, Math.round(s * 100) / 100);
}
