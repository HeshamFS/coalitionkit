// SPDX-License-Identifier: Apache-2.0
// The room's QR as shapes: round modules, square finders, and the goal dot at the centre where the
// room mark has it. High error correction is what lets the goal dot sit on top of the code.
import qrcode from "qrcode-generator";

/** The drawing is 480 wide. The white plate holds the code; the seats ring around it. */
export const VIEW = 480;
export const PLATE = { x: 100, y: 100, size: 280, pad: 16, radius: 16 };
export const SEAT_RING = 220;
const GOAL_CLEAR = 28;
const GOAL_DOT = 17;
const DOT_SHARE = 0.44;

export type QrMark =
  | { kind: "dot"; x: number; y: number; r: number }
  | { kind: "square"; x: number; y: number; size: number };

export type QrShapes = {
  marks: QrMark[];
  goal: { x: number; y: number; clear: number; dot: number };
};

/** The patterns a reader locks on to. They stay square, or cameras can't find the code. */
function guideCells(n: number) {
  const version = (n - 17) / 4;
  const count = version < 2 ? 0 : Math.floor(version / 7) + 2;
  const step = version === 32 ? 26 : Math.ceil((n - 13) / (count * 2 - 2)) * 2;
  const centres = Array.from({ length: count }, (_, i) =>
    i === 0 ? 6 : n - 7 - (count - 1 - i) * step,
  );
  const finder = (r: number, c: number) =>
    (c < 8 && r < 8) || (c >= n - 8 && r < 8) || (c < 8 && r >= n - 8);
  const aligned = (r: number, c: number) =>
    centres.some((y) =>
      centres.some((x) => Math.abs(r - y) <= 2 && Math.abs(c - x) <= 2 && !finder(y, x)),
    );
  return (r: number, c: number) => finder(r, c) || aligned(r, c);
}

export function qrShapes(text: string): QrShapes {
  const q = qrcode(0, "H");
  q.addData(text);
  q.make();
  const n = q.getModuleCount();
  const size = (PLATE.size - 2 * PLATE.pad) / n;
  const left = PLATE.x + PLATE.pad;
  const top = PLATE.y + PLATE.pad;
  const guide = guideCells(n);
  const marks: QrMark[] = [];
  for (let r = 0; r < n; r++) {
    for (let c = 0; c < n; c++) {
      if (!q.isDark(r, c)) continue;
      if (guide(r, c))
        marks.push({ kind: "square", x: left + c * size, y: top + r * size, size: size + 0.1 });
      else
        marks.push({
          kind: "dot",
          x: left + (c + 0.5) * size,
          y: top + (r + 0.5) * size,
          r: size * DOT_SHARE,
        });
    }
  }
  const middle = PLATE.x + PLATE.size / 2;
  return { marks, goal: { x: middle, y: middle, clear: GOAL_CLEAR, dot: GOAL_DOT } };
}

/** Where each seat sits on the ring, leaving the same opening at the right as the room mark. */
export function seatSpots(seats: number): { x: number; y: number; r: number }[] {
  const middle = VIEW / 2;
  const ring = SEAT_RING;
  const opening = 34;
  const span = 360 - 2 * opening;
  const spacing = seats > 1 ? ((span / (seats - 1)) * Math.PI * ring) / 180 : 1000;
  const r = Math.min(13, spacing * 0.36);
  return Array.from({ length: seats }, (_, i) => {
    const turn = seats > 1 ? i / (seats - 1) : 0.5;
    const angle = ((opening + span * turn) * Math.PI) / 180;
    return { x: middle + ring * Math.cos(-angle), y: middle + ring * Math.sin(-angle), r };
  });
}
