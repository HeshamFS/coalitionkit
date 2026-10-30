// SPDX-License-Identifier: Apache-2.0
import { Bar, num, type Props, rows, type Send, text } from "../f08/shared";
import "../../styles/f09.css";
export function StepProgress({ p }: { p: Props; send: Send }) {
  const measured = rows(p.measured),
    planned = rows(p.planned);
  const all = [...measured, ...planned];
  const max = Math.max(1, ...all.map((r) => num(r.value)));
  const end = Math.max(1, ...all.map((r) => num(r.t)));
  const points = (items: Props[]) =>
    items.map((r) => `${(num(r.t) / end) * 260},${85 - (num(r.value) / max) * 65}`).join(" ");
  const last = measured.at(-1);
  return (
    <div className="card f09-progress">
      <div className="row">
        <span className="mono st">
          {text(p.task).includes(" · ") ? text(p.task).split(" · ")[0] : ""}
        </span>
        <b>{text(p.task).split(" · ").at(-1)}</b>
        <span className="h-right num small">{text(p.eta)}</span>
      </div>
      <svg viewBox="0 0 260 90" role="img" aria-label="Planned and measured readings">
        <title>Planned and measured readings</title>
        <polyline
          points={points(planned)}
          fill="none"
          stroke="var(--line-strong)"
          strokeDasharray="4 4"
        />
        <polyline points={points(measured)} fill="none" stroke="var(--blue)" strokeWidth="2.5" />
        {last && (
          <>
            <circle
              cx={(num(last.t) / end) * 260}
              cy={85 - (num(last.value) / max) * 65}
              r="4"
              fill="var(--blue)"
            />
            <text
              x={(num(last.t) / end) * 260 + 6}
              y={81 - (num(last.value) / max) * 65}
              fontFamily="var(--font-mono)"
              fontSize="9"
              fill="var(--blue-text)"
            >
              {text(last.label) || text(last.value)}
            </text>
          </>
        )}
        <text x="4" y="78" fontFamily="var(--font-mono)" fontSize="8" fill="var(--ink-3)">
          planned · measured
        </text>
      </svg>
      <Bar value={num(p.progress)} />
      <span className="small">{text(last?.source)}</span>
    </div>
  );
}
