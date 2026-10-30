// SPDX-License-Identifier: Apache-2.0
import type { ComponentContext } from "@a2ui/web_core/v0_9";
import { createContext, Fragment, type ReactNode, useContext } from "react";
export const PreviewState = createContext<string | undefined>(undefined);
export const usePreviewState = () => useContext(PreviewState);
export type Props = Record<string, unknown>;
export type Send = (event: string, data?: Props) => void;
export const obj = (v: unknown): Props =>
  v && typeof v === "object" && !Array.isArray(v) ? (v as Props) : {};
export const list = (v: unknown): unknown[] => (Array.isArray(v) ? v : []);
export const rows = (v: unknown): Props[] => list(v).map(obj);
export const num = (v: unknown): number => (typeof v === "number" ? v : Number(obj(v).value ?? 0));
export const text = (v: unknown): string => {
  if (v === undefined || v === null) return "";
  if (typeof v !== "object") return String(v);
  if (Array.isArray(v)) return v.map(text).join(" · ");
  const o = obj(v);
  return text(o.label ?? o.name ?? o.value ?? o.id ?? o.text ?? "");
};
export function sendFor(context: ComponentContext): Send {
  return (name, data = {}) => {
    void context.dispatchAction({ event: { name, context: data } });
  };
}
export function Action({
  label,
  event,
  send,
  data,
  disabled,
  primary = false,
}: {
  label: string;
  event: string;
  send: Send;
  data?: Props;
  disabled?: boolean;
  primary?: boolean;
}) {
  return (
    <button
      type="button"
      className={`btn btn-sm${primary ? " btn-primary" : ""}`}
      disabled={disabled}
      onClick={() => send(event, data)}
    >
      {label}
    </button>
  );
}
export function Card({
  name,
  children,
  state,
  tone = "",
}: {
  name: string;
  children: ReactNode;
  state?: string;
  tone?: string;
}) {
  return (
    <section
      className={`${["ApprovalButton", "ConsentCard", "DisclosureLadder", "ScopeBadge", "PrivateField", "OverlapView", "WhatOthersKnow", "StaleNotice", "DurableConsent", "DecisionLog"].includes(name) ? "f08-content" : "card"} family-card ${tone}`}
      data-component={name}
      data-state={usePreviewState() ?? state}
      aria-label={name}
    >
      {children}
    </section>
  );
}
export function Badge({ children, tone = "estimate" }: { children: ReactNode; tone?: string }) {
  return <span className={`badge b-${tone}`}>{children}</span>;
}
export function Fields({ values }: { values: Props }) {
  return (
    <dl className="kv">
      {Object.entries(values).map(([k, v]) => (
        <Fragment key={k}>
          <dt>{k}</dt>
          <dd>{text(v)}</dd>
        </Fragment>
      ))}
    </dl>
  );
}
export function Table({ data, columns }: { data: unknown; columns: string[] }) {
  return (
    <div className="family-table">
      <table className="tbl">
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c}>{c}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows(data).map((r, i) => (
            <tr key={text(r.id) || `${i}`}>
              {columns.map((c) => (
                <td key={c}>{text(r[c])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
export function Bar({ value }: { value: number }) {
  return (
    // biome-ignore lint/a11y/useSemanticElements: the styled meter preserves the sheet geometry
    <div
      className="bar"
      role="meter"
      aria-label="Progress"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={Math.round(Math.max(0, Math.min(1, value)) * 100)}
    >
      <span style={{ width: `${Math.round(Math.max(0, Math.min(1, value)) * 100)}%` }} />
    </div>
  );
}
export function Checks({ items }: { items: unknown }) {
  return (
    <ul className="family-list">
      {rows(items).map((r, i) => (
        <li className="row" key={text(r.name) || `${i}`}>
          <span className={r.state === "failed" ? "family-bad" : "family-ok"}>
            {r.state === "passed" || r.state === "done" ? "✓" : r.state === "failed" ? "×" : "◌"}
          </span>
          <span className="grow">{text(r.name)}</span>
          <Badge>{text(r.state)}</Badge>
          <span className="st">{text(r.detail ?? r.took)}</span>
        </li>
      ))}
    </ul>
  );
}
export function Chart({
  series,
  planned,
  unit,
}: {
  series: unknown;
  planned?: unknown;
  unit?: unknown;
}) {
  const values = rows(series);
  const all = [...values, ...rows(planned)];
  const max = Math.max(1, ...all.map((v) => num(v.value)));
  const min = Math.min(0, ...all.map((v) => num(v.value)));
  const points = (data: Props[]) =>
    data
      .map(
        (v, i) =>
          `${36 + (i * 524) / Math.max(1, data.length - 1)},${168 - ((num(v.value) - min) / (max - min)) * 140}`,
      )
      .join(" ");
  return (
    <>
      <svg
        viewBox="0 0 600 190"
        className="family-chart"
        role="img"
        aria-label={`Measured and planned readings ${text(unit)}`}
      >
        <title>Measured and planned readings</title>
        {[18, 68, 118, 168].map((y) => (
          <path key={y} d={`M36 ${y} H600`} stroke="var(--line)" />
        ))}
        <polyline
          points={points(rows(planned))}
          fill="none"
          stroke="var(--line-strong)"
          strokeDasharray="5 4"
          strokeWidth="1.5"
        />
        <polyline points={points(values)} fill="none" stroke="var(--blue)" strokeWidth="2.5" />
        <text x="40" y="186" fill="var(--ink-3)" fontSize="10">
          {text(values[0]?.t)}
        </text>
        <text x="480" y="186" fill="var(--ink-3)" fontSize="10">
          {text(values.at(-1)?.t)}
        </text>
      </svg>
      <details>
        <summary>Table view</summary>
        <Table data={series} columns={["t", "value", "confidence"]} />
      </details>
    </>
  );
}
