// SPDX-License-Identifier: Apache-2.0
import { Frame, list, num, type Props, rows, str } from "../f05/shared";
export function ObjectiveBars({ p }: Props) {
  const objectives = rows(p.objectives);
  return (
    <Frame name="ObjectiveBars" className="f06-objectives">
      {objectives.map((r) => {
        const width = Math.max(0, Math.min(100, (num(r.value) / num(r.scale, 100)) * 100));
        return (
          <div className="row small" key={str(r.name)}>
            <span className="f06-objective-name">{str(r.name)}</span>
            {/* biome-ignore lint/a11y/useSemanticElements: custom bar preserves the reference geometry across browsers */}
            <div
              className="bar grow"
              role="meter"
              aria-label={str(r.name)}
              aria-valuenow={num(r.value)}
              aria-valuemin={0}
              aria-valuemax={num(r.scale, 100)}
              title={`${r.better === "lower" ? "Lower" : "Higher"} is better`}
            >
              <span
                style={{
                  width: `${width}%`,
                  background:
                    r.tone === "warn"
                      ? "var(--warn-fg)"
                      : r.muted
                        ? "var(--line-strong)"
                        : undefined,
                }}
              />
            </div>
            <span
              className="num f06-objective-value"
              title={str(
                r.value && typeof r.value === "object"
                  ? (r.value as Record<string, unknown>).event_ref
                  : "",
              )}
            >
              {str(r.display) ||
                (str(r.unit) === "€"
                  ? `€${str(r.value)}`
                  : `${str(r.value)}${r.unit ? ` ${str(r.unit)}` : ""}`)}
            </span>
          </div>
        );
      })}
    </Frame>
  );
}
export function FairnessMeter({ p }: Props) {
  const data = rows(p.rows);
  return (
    <Frame name="FairnessMeter" className="f06-fairness">
      {data.map((r) => (
        <div
          key={str(r.participant)}
          className={`col f06-fairness-row ${num(r.share) > num(p.cap, 100) ? "f06-over" : ""}`}
        >
          <div className="row small">
            <span
              className={`av av-xs ${str(r.participant).endsWith("A") ? "s3" : str(r.participant).endsWith("C") ? "s5" : "s1"}`}
            >
              {str(r.participant).slice(-1)}
            </span>
            <span className="f06-participant">{str(r.participant)}</span>
            <span className="h-right num">
              {str(r.hours)} h · {str(r.share)} %
            </span>
          </div>
          {/* biome-ignore lint/a11y/useSemanticElements: the load meter includes a separate charter cap marker */}
          <div
            className="f06-load"
            role="meter"
            aria-label={`${str(r.participant)} share`}
            aria-valuenow={num(r.share)}
            aria-valuemin={0}
            aria-valuemax={100}
          >
            <div className="f06-load-track" />
            <div
              className="f06-load-fill"
              style={{ width: `${Math.max(0, Math.min(100, num(r.share)))}%` }}
            />
            <div className="f06-load-cap" style={{ left: `${num(p.cap, 100)}%` }} />
          </div>
          {num(r.share) > num(p.cap, 100) && (
            <span className="small">Over cap: {str(r.rule) || "charter load rule"}</span>
          )}
        </div>
      ))}
      <div className="row small">
        <i className="f06-key-cap" />
        cap {str(p.cap)} %{data[0]?.rule ? ` (${str(data[0].rule)})` : " (charter)"}
      </div>
    </Frame>
  );
}
export { Gantt } from "./gantt";

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
    <Frame name="DependencyGraph" className="f06-graph" state={p.changed ? "ripple" : "default"}>
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
              className={changed ? "f06-flow" : undefined}
              strokeWidth="1.5"
            />
          );
        })}
        {nodes.map((node) => {
          const at = pos.get(str(node.task));
          if (!at) return null;
          const changed = node.task === p.changed,
            invalidated = list(p.invalidated).includes(node.task),
            done = node.status === "done";
          const nodeWidth = at.x + 124 >= width ? 110 : 96;
          const ink =
            changed || invalidated ? "var(--blue-text)" : done ? "var(--ok-fg)" : "var(--ink-3)";
          return (
            <g key={str(node.task)}>
              <rect
                x={at.x}
                y={at.y}
                width={nodeWidth}
                height="36"
                rx="8"
                fill={invalidated ? "var(--blue-tint)" : done ? "var(--ok-bg)" : "var(--surface)"}
                stroke={
                  changed
                    ? "var(--blue)"
                    : invalidated
                      ? "var(--blue-line)"
                      : done
                        ? "var(--f06-ok-line)"
                        : "var(--line)"
                }
                strokeWidth={changed ? 2 : 1}
              />
              <text
                x={at.x + 10}
                y={at.y + 22}
                fontSize="11"
                fontWeight={changed || done ? 600 : 400}
                fill={ink}
              >
                {str(node.task)}
                {node.title ? ` ${str(node.title)}` : ""}
                {changed ? " ✎" : done ? " ✓" : ""}
              </text>
              <foreignObject x={at.x} y={at.y} width={nodeWidth} height="36">
                <button
                  type="button"
                  className="f06-diagram-target"
                  aria-label={str(node.task)}
                  onClick={() => send("task.open", { id: node.task })}
                />
              </foreignObject>
            </g>
          );
        })}
      </svg>
      {Boolean(p.changed) && (
        <div className="row small">
          <span className="tag t-changed">Changed</span>
          {str(nodes.find((n) => n.task === p.changed)?.change) || `${str(p.changed)} changed`} →{" "}
          <b>{list(p.invalidated).length} tasks</b> go back to negotiating;{" "}
          {nodes
            .filter((n) => n.task !== p.changed && !list(p.invalidated).includes(n.task))
            .map((n) => str(n.task))
            .join(" and ")}{" "}
          stay as they are.
        </div>
      )}
    </Frame>
  );
}
