// SPDX-License-Identifier: Apache-2.0
import type { ReactNode } from "react";
export type Props = {
  p: Record<string, unknown>;
  send: (event: string, data?: Record<string, unknown>) => void;
};
export const obj = (v: unknown): Record<string, unknown> =>
  v && typeof v === "object" && !Array.isArray(v) ? (v as Record<string, unknown>) : {};
export const list = (v: unknown): unknown[] => (Array.isArray(v) ? v : []);
export const rows = (v: unknown) => list(v).map(obj);
export const str = (v: unknown): string =>
  typeof v === "string"
    ? v
    : typeof v === "boolean"
      ? v
        ? "Yes"
        : "No"
      : typeof v === "number"
        ? String(v)
        : v && typeof v === "object"
          ? str(obj(v).label ?? obj(v).name ?? obj(v).value ?? obj(v).id)
          : "";
export const num = (v: unknown, fallback = 0): number =>
  typeof obj(v).value === "number"
    ? (obj(v).value as number)
    : typeof v === "number"
      ? v
      : fallback;
export const texts = (v: unknown) => list(v).map(str).join(" · ");
export function Frame({
  name,
  state,
  children,
  className = "",
}: {
  name: string;
  state?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section data-component={name} data-state={state} className={`f-catalog ${className}`}>
      {children}
    </section>
  );
}
export function Action({
  children,
  onClick,
  disabled = false,
}: {
  children: ReactNode;
  onClick: () => void;
  disabled?: boolean;
}) {
  return (
    <button type="button" className="btn btn-sm" disabled={disabled} onClick={onClick}>
      {children}
    </button>
  );
}
export function Mark({ state }: { state: unknown }) {
  const s = str(state);
  return <span className={`f-mark f-mark-${s}`}>{s}</span>;
}
export function Person({ name, seat = 1 }: { name: unknown; seat?: number }) {
  return (
    <span className="row">
      <span
        aria-hidden="true"
        className="av"
        style={{ background: `var(--seat-${Math.max(1, Math.min(5, seat))})` }}
      >
        {str(name).slice(-1)}
      </span>
      <span>{str(name)}</span>
    </span>
  );
}
export function Meter({ value, label }: { value: number; label: string }) {
  return (
    <meter
      className="f-meter"
      aria-label={label}
      value={Math.max(0, Math.min(100, value))}
      min={0}
      max={100}
    >
      {Math.max(0, Math.min(100, value))}%
    </meter>
  );
}
