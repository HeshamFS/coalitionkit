// SPDX-License-Identifier: Apache-2.0
// The ground of the map: a field of dots from a fixed pattern, so it looks the same on every visit.
// The only live colour comes from the rooms: dots around a room turn blue as its seats fill.
import { useEffect, useRef } from "react";
import type { Room, Spot } from "./rooms";

function hash(x: number, y: number) {
  const s = Math.sin(x * 127.1 + y * 311.7) * 43758.5453;
  return s - Math.floor(s);
}

function noise(x: number, y: number) {
  const [i, j] = [Math.floor(x), Math.floor(y)];
  const [f, g] = [x - i, y - j];
  const [u, v] = [f * f * (3 - 2 * f), g * g * (3 - 2 * g)];
  const top = hash(i, j) * (1 - u) + hash(i + 1, j) * u;
  const bottom = hash(i, j + 1) * (1 - u) + hash(i + 1, j + 1) * u;
  return top * (1 - v) + bottom * v;
}

const field = (x: number, y: number) =>
  noise(x, y) * 0.6 + noise(x * 2.1, y * 2.1) * 0.28 + noise(x * 4.3, y * 4.3) * 0.12;

type Point = readonly [number, number];

const ROADS: readonly (readonly Point[])[] = [
  [
    [0, 0.56],
    [0.22, 0.5],
    [0.42, 0.56],
    [0.58, 0.5],
    [0.8, 0.58],
    [1, 0.5],
  ],
  [
    [0.3, 0],
    [0.33, 0.28],
    [0.42, 0.56],
    [0.4, 0.8],
    [0.46, 1],
  ],
  [
    [0.58, 0.5],
    [0.66, 0.72],
    [0.82, 0.84],
    [1, 0.9],
  ],
  [
    [0.1, 1],
    [0.2, 0.72],
    [0.42, 0.56],
  ],
  [
    [0.58, 0.5],
    [0.72, 0.3],
    [0.88, 0.22],
    [1, 0.1],
  ],
];

function toSegment(px: number, py: number, a: Point, b: Point) {
  const [dx, dy] = [b[0] - a[0], b[1] - a[1]];
  const t = Math.max(0, Math.min(1, ((px - a[0]) * dx + (py - a[1]) * dy) / (dx * dx + dy * dy)));
  return Math.hypot(px - a[0] - t * dx, py - a[1] - t * dy);
}

function onRoad(nx: number, ny: number, aspect: number) {
  return ROADS.some((road) =>
    road.some((p, i) => {
      const q = road[i + 1];
      return (
        q !== undefined &&
        toSegment(nx, ny * aspect, [p[0], p[1] * aspect], [q[0], q[1] * aspect]) < 0.005
      );
    }),
  );
}

function draw(canvas: HTMLCanvasElement, rooms: Room[], where: Spot[]) {
  const [w, h] = [canvas.clientWidth, canvas.clientHeight];
  const g = w && h ? canvas.getContext("2d") : null;
  if (!g) return;
  const scale = Math.min(globalThis.devicePixelRatio || 1, 2);
  canvas.width = w * scale;
  canvas.height = h * scale;
  g.scale(scale, scale);
  const css = getComputedStyle(canvas);
  const color = (name: string) => css.getPropertyValue(name).trim();
  const [dotColor, roadColor, blue] = [color("--map-dot"), color("--map-road"), color("--blue")];
  const glows = rooms.map((room, i) => ({
    x: ((where[i]?.x ?? 0) / 100) * w,
    y: ((where[i]?.y ?? 0) / 100) * h,
    reach: (34 + (room.filled / room.seats) * 58) * Math.min(1, w / 900),
  }));
  const step = w < 600 ? 10 : 12;
  for (let y = step / 2; y < h; y += step) {
    for (let x = step / 2; x < w; x += step) {
      const [nx, ny] = [x / w, y / h];
      const road = onRoad(nx, ny, h / w);
      const land = field(nx * 5 + 3, ny * 4 + 7) > 0.34;
      const heat = Math.max(0, ...glows.map((c) => 1 - Math.hypot(x - c.x, y - c.y) / c.reach));
      if (!land && !road && heat <= 0) continue;
      g.globalAlpha = heat > 0 ? 0.55 + heat * 0.45 : 1;
      g.fillStyle = heat > 0 ? blue : road ? roadColor : dotColor;
      g.beginPath();
      g.arc(x, y, heat > 0 ? 1.5 + heat * 1.1 : road ? 1.6 : 1.25, 0, Math.PI * 2);
      g.fill();
    }
  }
  g.globalAlpha = 1;
}

export function DotMap({ rooms, where, theme }: { rooms: Room[]; where: Spot[]; theme: string }) {
  const ref = useRef<HTMLCanvasElement>(null);
  // biome-ignore lint/correctness/useExhaustiveDependencies: theme changes the colours read in draw
  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const paint = () => draw(canvas, rooms, where);
    paint();
    if (typeof ResizeObserver === "undefined") return;
    const watch = new ResizeObserver(paint);
    watch.observe(canvas);
    return () => watch.disconnect();
  }, [rooms, where, theme]);
  return <canvas ref={ref} className="ld-canvas" />;
}
