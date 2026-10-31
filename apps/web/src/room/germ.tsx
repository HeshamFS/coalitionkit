// SPDX-License-Identifier: Apache-2.0
// Germination for the room: each card assembles (skeleton, filled, one flash) in reading order.
import { type CSSProperties, createContext, type ReactNode, useContext } from "react";
import { Assemble } from "../ui/Assemble";

const GermStep = createContext(90);
/** Tests set the stagger to 0; the product keeps the default of about 90 ms. */
export const GermStepProvider = GermStep.Provider;

/** Cells beyond this index share the last delay, so a long list never waits too long. */
const MAX_STAGGER = 12;

export function Germ({
  index,
  ready,
  label,
  className,
  children,
}: {
  index: number;
  ready: boolean;
  /** The catalog name shown on the skeleton. */
  label: string;
  className?: string;
  children: ReactNode;
}) {
  const step = useContext(GermStep);
  return (
    <div
      className={["room-cell", className].filter(Boolean).join(" ")}
      style={{ "--i": Math.min(index, MAX_STAGGER) } as CSSProperties}
    >
      <Assemble ready={ready} label={label} delay={Math.min(index, MAX_STAGGER) * step}>
        {children}
      </Assemble>
    </div>
  );
}
