// SPDX-License-Identifier: Apache-2.0
// The Prism transition for "View as": the current cards fade out in reverse order, then the new
// view assembles in. `target` is the committed view; `phase` drives the CSS.
import { useCallback, useEffect, useRef, useState } from "react";

export type PrismPhase = "idle" | "out" | "in";
/** Longest reverse stagger (12 cells x 30 ms) plus the 200 ms fade. */
export const PRISM_OUT_MS = 560;

const reducedMotion = () => globalThis.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches;

export function usePrism(outMs = PRISM_OUT_MS) {
  const [target, setTarget] = useState<string | null>(null);
  const [phase, setPhase] = useState<PrismPhase>("idle");
  const timers = useRef<number[]>([]);
  const clear = useCallback(() => {
    for (const t of timers.current) clearTimeout(t);
    timers.current = [];
  }, []);
  useEffect(() => clear, [clear]);

  const go = useCallback(
    (next: string | null) => {
      clear();
      const commit = () => {
        setTarget(next);
        setPhase("in");
        timers.current.push(window.setTimeout(() => setPhase("idle"), 1200));
      };
      if (reducedMotion() || outMs <= 0) return commit();
      setPhase("out");
      timers.current.push(window.setTimeout(commit, outMs));
    },
    [clear, outMs],
  );
  const reset = useCallback(() => {
    clear();
    setTarget(null);
    setPhase("idle");
  }, [clear]);
  return { target, phase, go, reset };
}
