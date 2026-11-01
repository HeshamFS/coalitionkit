// SPDX-License-Identifier: Apache-2.0
/** Deterministic plan-graph layout and ripple counts. Pure functions, no randomness. */

export type RippleNode = { id: string; label: string; status?: string };
export type RippleEdge = { from: string; to: string };
export type RippleInfo = {
  seq: number;
  /** The task the change started at, when the event names one that is in the graph. */
  origin?: string;
  invalidated: string[];
  change?: string;
};

export const NODE_W = 148;
export const NODE_H = 34;
export const COL_GAP = 64;
export const ROW_GAP = 18;
export const PAD = 24;

export type Placed = RippleNode & { x: number; y: number; depth: number };

/** Longest-path depth per node; edges that would close a cycle are ignored. */
export function depths(nodes: RippleNode[], edges: RippleEdge[]): Map<string, number> {
  const ids = new Set(nodes.map((n) => n.id));
  const valid = edges.filter((e) => ids.has(e.from) && ids.has(e.to) && e.from !== e.to);
  const depth = new Map(nodes.map((n) => [n.id, 0]));
  for (let pass = 0; pass < nodes.length; pass++) {
    let moved = false;
    for (const e of valid) {
      const next = (depth.get(e.from) ?? 0) + 1;
      if (next > (depth.get(e.to) ?? 0) && next < nodes.length) {
        depth.set(e.to, next);
        moved = true;
      }
    }
    if (!moved) break;
  }
  return depth;
}

export function layout(
  nodes: RippleNode[],
  edges: RippleEdge[],
): { placed: Placed[]; width: number; height: number } {
  const depth = depths(nodes, edges);
  const rows = new Map<number, number>();
  const placed = nodes.map((n) => {
    const d = depth.get(n.id) ?? 0;
    const row = rows.get(d) ?? 0;
    rows.set(d, row + 1);
    return {
      ...n,
      depth: d,
      x: PAD + d * (NODE_W + COL_GAP),
      y: PAD + row * (NODE_H + ROW_GAP),
    };
  });
  const cols = Math.max(0, ...placed.map((p) => p.depth)) + 1;
  const tallest = Math.max(1, ...rows.values());
  return {
    placed,
    width: PAD * 2 + cols * NODE_W + (cols - 1) * COL_GAP,
    height: PAD * 2 + tallest * NODE_H + (tallest - 1) * ROW_GAP,
  };
}

export type RippleCounts = { touched: string[]; k: number; n: number; rest: number };

/** Touched tasks are the invalidated ones that exist in the graph; the origin is the cause, not a re-plan. */
export function rippleCounts(nodes: RippleNode[], ripple?: RippleInfo): RippleCounts {
  const known = new Set(nodes.map((n) => n.id));
  const touched = ripple
    ? ripple.invalidated.filter((id, i, all) => known.has(id) && all.indexOf(id) === i)
    : [];
  const n = nodes.length;
  return { touched, k: touched.length, n, rest: n - touched.length };
}

/** Edges into a touched task carry the wave. */
export function touchedEdge(e: RippleEdge, touched: Set<string>, origin?: string): boolean {
  return touched.has(e.to) && (touched.has(e.from) || e.from === origin);
}
