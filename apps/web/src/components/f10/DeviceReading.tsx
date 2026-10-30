// SPDX-License-Identifier: Apache-2.0
import { useState } from "react";
import { list, num, type Props, rows, type Send, Table, text } from "../f08/shared";
import "../../styles/f10.css";

const minutes = (value: unknown) => {
  const raw = text(value);
  if (raw.includes("T")) return Date.parse(raw) / 60000;
  const parts = raw.split(":").map(Number);
  return (parts[0] ?? 0) * 60 + (parts[1] ?? 0) + (parts[2] ?? 0) / 60;
};
function chartData(p: Props) {
  const series = rows(p.series),
    planned = rows(p.planned),
    all = [...series, ...planned];
  const times = all.map((r) => minutes(r.t)).filter(Number.isFinite);
  const start = times.length ? Math.min(...times) : 0,
    end = times.length ? Math.max(...times) : 60;
  const maximum = Math.max(1, ...all.map((r) => num(r.value)), ...list(p.limits).map(num));
  const x = (r: Props) => 40 + ((minutes(r.t) - start) / Math.max(1, end - start)) * 480;
  const y = (r: Props) => 18 + ((maximum - num(r.value)) / maximum) * 200;
  const points = (data: Props[]) => data.map((r) => `${x(r)},${y(r)}`).join(" ");
  return { series, planned, start, end, maximum, x, y, points, latest: series.at(-1) };
}
function ReadingChart({ p }: { p: Props }) {
  const { series, planned, start, end, maximum, x, y, points, latest } = chartData(p);
  return (
    <svg
      className="f10-chart"
      viewBox="0 0 600 190"
      role="img"
      aria-label={`Measured and planned readings ${text(p.unit)}`}
    >
      {[1, 0.75, 0.5, 0.25].map((ratio, i) => (
        <g key={ratio}>
          <text x="0" y={22 + i * 50} className="f10-axis">
            {maximum * ratio}
          </text>
          <path d={`M36 ${18 + i * 50} H600`} stroke="var(--line)" />
        </g>
      ))}
      {[0, 1, 2, 3].map((i) => (
        <text key={i} x={40 + i * 160} y="186" className="f10-axis">
          {`${Math.floor((start + ((end - start) * i) / 3) / 60) % 24}`.padStart(2, "0")}:
          {`${Math.round((start + ((end - start) * i) / 3) % 60)}`.padStart(2, "0")}
        </text>
      ))}
      {list(p.limits).map((limit) => (
        <g key={text(limit)}>
          <rect
            x="36"
            y={18 + ((maximum - num(limit)) / maximum) * 200}
            width="564"
            height="10"
            fill="var(--bad-bg)"
          />
          <text x="520" y="15" className="f10-limit">
            limit {num(limit).toLocaleString("fr-FR")} {text(p.unit)}
          </text>
        </g>
      ))}
      <polyline
        points={points(planned)}
        fill="none"
        stroke="var(--line-strong)"
        strokeWidth="1.5"
        strokeDasharray="5 4"
      />
      <polyline points={points(series)} fill="none" stroke="var(--blue)" strokeWidth="2.5" />
      {latest && (
        <g>
          <circle cx={x(latest)} cy={y(latest)} r="4.5" fill="var(--blue)" />
          <rect
            x={Math.min(438, x(latest) + 8)}
            y={y(latest) + 6}
            width="96"
            height="30"
            rx="6"
            fill="var(--surface)"
            stroke="var(--line)"
          />
          <text x={Math.min(446, x(latest) + 16)} y={y(latest) + 20} className="f10-value">
            {num(latest.value).toLocaleString("fr-FR")} {text(p.unit)}
          </text>
          <text x={Math.min(446, x(latest) + 16)} y={y(latest) + 31} className="f10-callout-time">
            {text(latest.t)} · conf {text(latest.confidence)}
          </text>
        </g>
      )}
      {rows(p.annotations).map((a) => (
        <g key={text(a.label)}>
          <path d={`M${x(a)} 18 V168`} stroke="var(--blue)" strokeDasharray="2 3" opacity=".5" />
          <text x={x(a) + 4} y="160" className="f10-annotation">
            {text(a.label)}
          </text>
        </g>
      ))}
    </svg>
  );
}
export function DeviceReading({ p, send }: { p: Props; send: Send }) {
  const [table, setTable] = useState(false);
  return (
    <>
      {table ? (
        <Table data={rows(p.series)} columns={["t", "value", "confidence"]} />
      ) : (
        <ReadingChart p={p} />
      )}
      <div className="row small">
        <span className="row">
          <span className="f10-measured-key" />
          measured
        </span>
        <span className="row">
          <span className="f10-planned-key" />
          planned
        </span>
        <span className="h-right">
          <button type="button" className="f10-link" onClick={() => setTable(!table)}>
            {table ? "chart view" : "table view"}
          </button>{" "}
          ·{" "}
          <button
            type="button"
            className="f10-link"
            aria-label="Export CSV"
            onClick={() => send("reading.export", { source: p.source })}
          >
            export CSV
          </button>
        </span>
      </div>
    </>
  );
}
