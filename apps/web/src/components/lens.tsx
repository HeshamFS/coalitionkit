// SPDX-License-Identifier: Apache-2.0
import type { ReactNode } from "react";

const DOTS = ["a", "b", "c", "d", "e", "f"] as const;

export type LensGesture = { gesture: "Tap" | "Swipe"; does: string; tone?: "blue" | "muted" };

export type LensCardProps = {
  eyebrow?: string;
  title: string;
  body?: string;
  /** Step position, drawn as the dots at the top right. */
  step?: { index: number; total: number };
  /** At most two gestures; the first is the primary one. */
  hints?: LensGesture[];
  state?: "shown" | "acknowledged";
  /** Extra content under the body (a result line). Plain text only. */
  children?: ReactNode;
};

/**
 * LensCard (sheet 09b): one card, one step, 600 x 600, black is transparent. Large type, high
 * contrast, no hover, no buttons: the wearer taps or swipes. The title is at least 22 px.
 */
export function LensCard({
  eyebrow,
  title,
  body,
  step,
  hints = [],
  state = "shown",
  children,
}: LensCardProps) {
  const shown = hints.slice(0, 2);
  return (
    <article className="lens-card" data-component="LensCard" data-state={state} aria-label={title}>
      <header className="lens-top">
        {eyebrow && <span className="lens-eyebrow">{eyebrow}</span>}
        {step && step.total > 1 && (
          <span className="lens-dots" aria-hidden="true">
            {DOTS.slice(0, Math.min(step.total, 6)).map((id, i) => (
              <span key={id} className={i === step.index ? "on" : undefined} />
            ))}
          </span>
        )}
      </header>
      <div className="lens-main">
        <h2 className="lens-title">{title}</h2>
        {body && <p className="lens-body">{body}</p>}
        {children}
      </div>
      <footer className="lens-hints">
        {shown.map((h) => (
          <span key={h.gesture} className={`lens-hint${h.tone === "muted" ? " muted" : ""}`}>
            {h.gesture === "Tap" && (
              <svg
                width="26"
                height="26"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.5"
                aria-hidden="true"
                focusable="false"
              >
                <path d="M5 12l5 5 9-10" />
              </svg>
            )}
            {h.gesture}: {h.does}
          </span>
        ))}
      </footer>
    </article>
  );
}

/** The 600 x 600 display. Black is transparent on the real glasses. */
export function LensFrame({ children, label }: { children: ReactNode; label?: string }) {
  return (
    <section className="lens-frame" aria-label={label ?? "Lens display, 600 by 600"}>
      {children}
    </section>
  );
}
