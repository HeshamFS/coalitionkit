// SPDX-License-Identifier: Apache-2.0
import { Frame, list, Meter, num, type Props, rows, str } from "../f05/shared";
export function ObjectiveBars({ p }: Props) {
  const objectives = rows(p.objectives),
    max = Math.max(1, ...objectives.map((r) => num(r.value)));
  return (
    <Frame name="ObjectiveBars">
      {objectives.map((r) => (
        <div className="f06-metric" key={str(r.name)}>
          <span>
            {str(r.name)} <small>{r.better === "lower" ? "↓" : "↑"}</small>
          </span>
          <Meter value={(100 * num(r.value)) / max} label={str(r.name)} />
          <span>
            {str(r.value)} {str(r.unit)}
          </span>
        </div>
      ))}
    </Frame>
  );
}
export function FairnessMeter({ p }: Props) {
  return (
    <Frame name="FairnessMeter">
      {rows(p.rows).map((r) => (
        <div
          key={str(r.participant)}
          className={`f06-metric ${num(r.share) > num(p.cap, 100) ? "f06-over" : ""}`}
        >
          <span>{str(r.participant)}</span>
          <div className="f06-cap">
            <Meter value={num(r.share)} label={`${str(r.participant)} share`} />
            <span style={{ left: `${num(p.cap, 100)}%` }} />
          </div>
          <span>
            {str(r.hours)} h · {str(r.share)}%
          </span>
        </div>
      ))}
      <small>Charter cap {str(p.cap)}% · agreed shares shown against current load</small>
    </Frame>
  );
}
const date = (v: unknown) => Date.parse(str(v));
export function Gantt({ p, send }: Props) {
  const data = rows(p.rows),
    starts = data.map((r) => date(r.start)).filter(Number.isFinite),
    ends = data.map((r) => date(r.end)).filter(Number.isFinite),
    start = Math.min(...starts),
    end = Math.max(...ends),
    span = Math.max(1, end - start),
    position = (v: unknown) => Math.max(0, Math.min(100, (100 * (date(v) - start)) / span));
  return (
    <Frame name="Gantt">
      <div className="f06-gantt">
        <div className="f06-axis">
          <span>{str(data[0]?.start)}</span>
          <span>{str(p.zoom)}</span>
          <span>{str(data.at(-1)?.end)}</span>
        </div>
        {data.map((r) => (
          <div className="f06-gantt-row" key={str(r.task)}>
            <span>{str(r.task)}</span>
            <div className="f06-gantt-track">
              <button
                type="button"
                className={`f06-taskbar ${list(p.criticalPath).includes(r.task) ? "critical" : ""}`}
                style={{
                  left: `${position(r.start)}%`,
                  width: `${Math.max(3, position(r.end) - position(r.start))}%`,
                }}
                onClick={() => send("task.open", { id: r.task })}
              >
                {str(r.assignee)} · {str(r.status)}
              </button>
              {Number.isFinite(date(p.now)) && (
                <span className="f06-now" style={{ left: `${position(p.now)}%` }} />
              )}
            </div>
          </div>
        ))}
      </div>
      <small>Critical path: {list(p.criticalPath).map(str).join(" → ")}</small>
      {list(p.deadlines).map((d) => (
        <small key={str(d)}>Deadline {str(d)}</small>
      ))}
    </Frame>
  );
}
function positions(nodes: Record<string, unknown>[], edges: Record<string, unknown>[]) {
  const rank = new Map(nodes.map((node) => [str(node.task), 0]));
  for (let i = 0; i < nodes.length; i++)
    for (const edge of edges)
      rank.set(
        str(edge.to),
        Math.min(
          nodes.length - 1,
          Math.max(rank.get(str(edge.to)) ?? 0, (rank.get(str(edge.from)) ?? 0) + 1),
        ),
      );
  return new Map(
    nodes.map((node) => {
      const level = rank.get(str(node.task)) ?? 0,
        peers = nodes.filter((n) => rank.get(str(n.task)) === level),
        index = peers.indexOf(node);
      return [str(node.task), { x: 6 + level * 124, y: peers.length === 1 ? 66 : 18 + index * 96 }];
    }),
  );
}
export function DependencyGraph({ p, send }: Props) {
  const nodes = rows(p.nodes),
    edges = rows(p.edges),
    pos = positions(nodes, edges),
    width = Math.max(620, ...Array.from(pos.values()).map((v) => v.x + 110));
  return (
    <Frame name="DependencyGraph" state={p.changed ? "ripple" : "default"}>
      <svg viewBox={`0 0 ${width} 170`} className="f06-dependency" aria-label="Task dependencies">
        {edges.map((edge) => {
          const from = pos.get(str(edge.from)),
            to = pos.get(str(edge.to));
          if (!from || !to) return null;
          const changed = list(p.invalidated).includes(edge.to);
          return (
            <path
              key={`${str(edge.from)}-${str(edge.to)}`}
              d={`M${from.x + 96} ${from.y + 18} C${from.x + 110} ${from.y + 18},${to.x - 14} ${to.y + 18},${to.x} ${to.y + 18}`}
              fill="none"
              stroke={changed ? "var(--blue)" : "var(--line-strong)"}
              strokeWidth="1.5"
            />
          );
        })}
        {nodes.map((node) => {
          const at = pos.get(str(node.task));
          return (
            <foreignObject key={str(node.task)} x={at?.x} y={at?.y} width="110" height="36">
              <button
                type="button"
                className={`f06-node ${node.task === p.changed ? "changed" : list(p.invalidated).includes(node.task) ? "invalidated" : node.status === "done" ? "done" : ""}`}
                onClick={() => send("task.open", { id: node.task })}
              >
                {str(node.task)}
                {node.status === "done" ? " ✓" : ""}
              </button>
            </foreignObject>
          );
        })}
      </svg>
      {Boolean(p.changed) && (
        <small>
          {str(p.changed)} changed → <b>{list(p.invalidated).length} tasks</b> go back to
          negotiating; other tasks stay as they are.
        </small>
      )}
    </Frame>
  );
}
