// SPDX-License-Identifier: Apache-2.0
// Germination: a composed component arrives as a labelled skeleton, fills, flashes once when it
// goes live, then settles (design system motion "Assemble": 450 ms, cubic-bezier(.2,0,0,1)).
// With reduced motion the component appears in place.
import { type ReactNode, useEffect, useRef, useState } from "react";
import "./assemble.css";

export type AssembleState = "skeleton" | "filled" | "live";

export function Assemble({
  ready,
  label,
  delay = 0,
  className,
  children,
}: {
  /** Content is available; until then the labelled skeleton shows. */
  ready: boolean;
  /** What is being composed, named as the catalog names it ("Seats it found", "PlanCard"). */
  label: string;
  /** Stagger in ms, so a surface assembles in reading order. */
  delay?: number;
  className?: string;
  children: ReactNode;
}) {
  const [state, setState] = useState<AssembleState>("skeleton");
  const timers = useRef<number[]>([]);
  useEffect(() => {
    for (const t of timers.current) clearTimeout(t);
    timers.current = [];
    if (!ready) {
      setState("skeleton");
      return;
    }
    timers.current.push(window.setTimeout(() => setState("filled"), delay));
    timers.current.push(window.setTimeout(() => setState("live"), delay + 450));
    return () => {
      for (const t of timers.current) clearTimeout(t);
    };
  }, [ready, delay]);
  return (
    <div
      className={["ck-assemble", className].filter(Boolean).join(" ")}
      data-assemble={state}
      aria-busy={state === "skeleton"}
    >
      {state === "skeleton" ? (
        <div className="ck-assemble-skel">
          <span className="ck-assemble-name">
            {label}
            <span className="sr-only"> is being composed</span>
          </span>
          <span className="ck-assemble-bar" style={{ width: "72%" }} />
          <span className="ck-assemble-bar" style={{ width: "46%" }} />
        </div>
      ) : (
        children
      )}
    </div>
  );
}
