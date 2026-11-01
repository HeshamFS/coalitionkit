// SPDX-License-Identifier: Apache-2.0
import { useVocabulary } from "../feed/vocabulary";
import {
  layout,
  NODE_H,
  NODE_W,
  type RippleEdge,
  type RippleInfo,
  type RippleNode,
  rippleCounts,
  touchedEdge,
} from "./graph";
import "./ripple.css";

export type RippleProps = {
  nodes: RippleNode[];
  edges: RippleEdge[];
  /** The latest ripple event in the viewer's scope; absent means nothing has changed. */
  ripple?: RippleInfo;
  /** People asked again, counted from visible events. Absent means the chip is left out. */
  peopleAsked?: number;
  /** Measured time to every affected screen in ms. Absent shows the [MEASURED] marker. */
  measuredMs?: number;
};

const clip = (s: string, max = 22) => (s.length > max ? `${s.slice(0, max - 1)}…` : s);

function edgePath(a: { x: number; y: number }, b: { x: number; y: number }) {
  const x1 = a.x + NODE_W;
  const y1 = a.y + NODE_H / 2;
  const x2 = b.x;
  const y2 = b.y + NODE_H / 2;
  const mid = (x1 + x2) / 2;
  return `M${x1} ${y1} C${mid} ${y1}, ${mid} ${y2}, ${x2} ${y2}`;
}

export function Ripple({ nodes, edges, ripple, peopleAsked, measuredMs }: RippleProps) {
  const { word } = useVocabulary();
  const tasks = word("task", 2);
  const { placed, width, height } = layout(nodes, edges);
  const counts = rippleCounts(nodes, ripple);
  const touched = new Set(counts.touched);
  const origin =
    ripple?.origin && nodes.some((n) => n.id === ripple.origin) ? ripple.origin : undefined;
  const at = new Map(placed.map((p) => [p.id, p]));
  const waveAt = at.get(origin ?? counts.touched[0] ?? "");
  const summary = ripple
    ? `Plan graph of ${counts.n} ${tasks}. ${counts.k} re-planned, ${counts.rest} untouched.`
    : `Plan graph of ${counts.n} ${tasks}. No change yet.`;
  return (
    <section className="mo-ripple" aria-label="Ripple">
      <p className="mo-eyebrow">The plan as a living graph</p>
      <h3>
        Something changes. <em>Only what it touches moves.</em>
      </h3>
      {/* biome-ignore lint/a11y/noNoninteractiveTabindex: a scrollable box must be reachable by keyboard */}
      <section className="mo-ripple-scroll" tabIndex={0} aria-label="Plan graph, scrolls sideways">
        {/* key restarts the one-shot animations when a new ripple arrives */}
        <svg
          key={ripple?.seq ?? 0}
          role="img"
          aria-label={summary}
          width={width}
          height={height}
          viewBox={`0 0 ${width} ${height}`}
        >
          {edges.map((e) => {
            const a = at.get(e.from);
            const b = at.get(e.to);
            if (!a || !b) return null;
            const hit = ripple ? touchedEdge(e, touched, origin) : false;
            return (
              <path
                key={`${e.from}>${e.to}`}
                className="mo-edge"
                data-touched={hit}
                style={{ "--delay": `${b.depth * 300}ms` } as React.CSSProperties}
                d={edgePath(a, b)}
              />
            );
          })}
          {waveAt ? (
            <circle
              className="mo-wave"
              cx={waveAt.x + NODE_W / 2}
              cy={waveAt.y + NODE_H / 2}
              r={40}
            />
          ) : null}
          {placed.map((p) => {
            const isTouched = touched.has(p.id);
            return (
              <g
                key={p.id}
                className="mo-node"
                data-task={p.id}
                data-touched={isTouched}
                data-pulse={isTouched}
                data-origin={p.id === origin}
                style={{ "--delay": `${p.depth * 300}ms` } as React.CSSProperties}
              >
                <title>{p.status ? `${p.label} · ${p.status}` : p.label}</title>
                <rect x={p.x} y={p.y} width={NODE_W} height={NODE_H} rx={10} />
                <text x={p.x + 12} y={p.y + NODE_H / 2 + 4.5}>
                  {clip(p.label)}
                </text>
              </g>
            );
          })}
        </svg>
      </section>
      <div className="mo-chips" aria-live="polite">
        {ripple ? (
          <>
            <span className="mo-chip">
              <b>{counts.k}</b> of {counts.n} {tasks} re-planned
            </span>
            <span className="mo-chip">
              {typeof peopleAsked === "number" ? (
                <>
                  <b>{peopleAsked}</b> {peopleAsked === 1 ? "person" : "people"} asked again ·{" "}
                </>
              ) : null}
              <b>{counts.rest}</b> untouched
            </span>
          </>
        ) : (
          <span className="mo-chip">No change yet: every {word("task")} holds</span>
        )}
        <span className="mo-chip">
          change to every affected screen{" "}
          <b>{typeof measuredMs === "number" ? `${measuredMs} ms` : "[MEASURED]"}</b>
        </span>
        {ripple ? (
          <p className="mo-mono">
            coalition.ripple · invalidates {ripple.invalidated.length} tasks
          </p>
        ) : null}
      </div>
    </section>
  );
}
