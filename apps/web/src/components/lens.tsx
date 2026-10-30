// SPDX-License-Identifier: Apache-2.0
import type { ReactNode } from "react";

export { LensCard, type LensCardProps, type LensGesture } from "./f02/LensCard";

/** The 600 x 600 display. Black is transparent on the real glasses. */
export function LensFrame({ children, label }: { children: ReactNode; label?: string }) {
  return (
    <section className="lens-frame" aria-label={label ?? "Lens display, 600 by 600"}>
      {children}
    </section>
  );
}
