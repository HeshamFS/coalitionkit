// SPDX-License-Identifier: Apache-2.0
import type { ReactNode } from "react";

export type Door = "wide" | "compact" | "lens" | "message" | "voice";

/** One component on the sheet: the component itself, its name, its doors, its props and events. */
export function Cell({
  name,
  props,
  events,
  doors,
  span,
  children,
}: {
  name: string;
  props: string;
  events?: string;
  doors?: Door[];
  span?: 2 | 3 | 4;
  children: ReactNode;
}) {
  return (
    <div className={`cell${span ? ` span${span}` : ""}`} data-component={name}>
      <div className="demo">{children}</div>
      <div className="cell-name">{name}</div>
      {doors && (
        <div className="door">
          {doors.map((d) => (
            <span key={d}>{d}</span>
          ))}
        </div>
      )}
      <div className="props">{props}</div>
      <div className="evts">{events ?? "display only"}</div>
    </div>
  );
}

export function Family({
  n,
  title,
  children,
  cols = 4,
}: {
  n: string;
  title: string;
  children: ReactNode;
  cols?: 3 | 4;
}) {
  return (
    <>
      <div className="fam">
        <span className="fam-n">{n}</span>
        <span className="fam-t">{title}</span>
        <span className="fam-line" />
      </div>
      <div className={`g${cols}`}>{children}</div>
    </>
  );
}

/** A small state label under a drawn state, as the sheets do. */
export function State({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="col" data-state-label={label}>
      {children}
      <span className="st">{label}</span>
    </div>
  );
}
