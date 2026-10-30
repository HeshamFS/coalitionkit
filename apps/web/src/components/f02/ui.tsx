// SPDX-License-Identifier: Apache-2.0
import { Fragment, type ReactNode } from "react";

export type Data = Record<string, unknown>;
export type View = {
  p: Data;
  send: (name: string, data?: Data) => void;
  build?: (id: string, basePath?: string) => ReactNode;
};
export const obj = (v: unknown): Data =>
  v && typeof v === "object" && !Array.isArray(v) ? (v as Data) : {};
export const text = (v: unknown): string =>
  typeof v === "string" ? v : typeof v === "number" ? String(v) : "";
export const list = (v: unknown): Data[] =>
  Array.isArray(v) ? v.map((x) => (typeof x === "string" ? { id: x, label: x } : obj(x))) : [];
export const label = (v: Data) => text(v.label ?? v.title ?? v.text ?? v.name ?? v.id);
export const number = (v: unknown, fallback = 0) =>
  typeof obj(v).value === "number" ? (obj(v).value as number) : fallback;
export const expired = (v: unknown) =>
  !!v && (!Number.isFinite(Date.parse(text(v))) || Date.parse(text(v)) <= Date.now());
export function Frame({
  name,
  state,
  children,
  tone = "",
}: {
  name: string;
  state?: string;
  children: ReactNode;
  tone?: string;
}) {
  return (
    <section className={`ck-family ck-${name} ${tone}`} data-component={name} data-state={state}>
      {children}
    </section>
  );
}
export function Action({
  children,
  onClick,
  primary,
  disabled,
  pressed,
}: {
  children: ReactNode;
  onClick: () => void;
  primary?: boolean;
  disabled?: boolean;
  pressed?: boolean;
}) {
  return (
    <button
      type="button"
      className={`ck-action${primary ? " ck-primary" : ""}`}
      disabled={disabled}
      aria-pressed={pressed}
      onClick={onClick}
    >
      {children}
    </button>
  );
}
export function Children({ value, build }: { value: unknown; build: View["build"] }) {
  const children = Array.isArray(value) ? value : value ? [value] : [];
  return (
    <>
      {children.map((c) => (
        <Fragment key={typeof c === "string" ? c : text(obj(c).id)}>
          {build?.(typeof c === "string" ? c : text(obj(c).id), text(obj(c).basePath) || undefined)}
        </Fragment>
      ))}
    </>
  );
}
export function Rows({ value, onPick }: { value: unknown; onPick?: (item: Data) => void }) {
  return (
    <div className="ck-rows">
      {list(value).map((item, i) => (
        <div className="ck-row" key={text(item.id ?? item.ref) || `${label(item)}-${i}`}>
          {onPick ? (
            <Action onClick={() => onPick(item)}>{label(item)}</Action>
          ) : (
            <span>{label(item)}</span>
          )}
          {item.summary ? <small>{text(item.summary)}</small> : null}
          {item.time ? <small>{text(item.time)}</small> : null}
        </div>
      ))}
    </div>
  );
}
export function Subject({ value }: { value: unknown }) {
  const s = obj(value);
  return (
    <span className="ck-meta">
      {text(s.kind)} {text(s.id)} · revision {number(s.revision)}
    </span>
  );
}
