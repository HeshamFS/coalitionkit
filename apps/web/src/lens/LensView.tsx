// SPDX-License-Identifier: Apache-2.0
import { type KeyboardEvent, useEffect, useMemo, useRef, useState } from "react";
import { LensCard, type LensGesture } from "../components/lens";
import { useAgentSnapshot, useFeedApi, useFeedSnapshot } from "../feed/useFeed";
import { buildSteps, type Gesture, type LensStep, press, START } from "./machine";

/** The catalog components the lens draws. Every one of them has `lens` among its doors. */
export const LENS_COMPONENTS = ["LensCard"] as const;

function hintsFor(step: LensStep | undefined): LensGesture[] {
  return [
    { gesture: "Tap", does: step?.kind === "phone" ? "next" : "got it" },
    { gesture: "Swipe", does: "next", tone: "muted" },
  ];
}

/**
 * The lens door (glasses simulator): one card, one step, 600 x 600. It reads the same feed as
 * the room. It never answers anything: a request is shown with "Decide on your phone".
 */
export function LensView() {
  const feed = useFeedSnapshot();
  const agent = useAgentSnapshot();
  const { signOut } = useFeedApi();
  const [machine, setMachine] = useState(START);
  const frame = useRef<HTMLDivElement>(null);

  const steps = useMemo(() => buildSteps(feed.state, agent.requests), [feed.state, agent.requests]);
  const index = Math.max(0, Math.min(machine.index, steps.length - 1));
  const step = steps[index];

  useEffect(() => frame.current?.focus(), []);

  const gesture = (g: Gesture) => setMachine((m) => press(m, steps, g));

  const onKey = (e: KeyboardEvent) => {
    const map: Record<string, Gesture> = {
      Enter: "tap",
      " ": "tap",
      ArrowRight: "next",
      ArrowLeft: "back",
    };
    const g = map[e.key];
    if (!g) return;
    e.preventDefault();
    gesture(g);
  };

  const card =
    !step || (feed.state === null && feed.status === "connecting") ? (
      <LensCard eyebrow="Coalition" title="Connecting" />
    ) : (
      <LensCard
        eyebrow={step.eyebrow}
        title={step.title}
        body={step.body}
        step={{ index, total: steps.length }}
        hints={hintsFor(step)}
      />
    );

  return (
    <main className="lens-page" data-testid="lens" data-step={step?.id ?? "none"}>
      <div className="lens-caps">Lens · 600 × 600 · black is transparent</div>
      <div
        ref={frame}
        role="application"
        className="lens-frame"
        aria-label="Lens display, 600 by 600"
        aria-live="polite"
        // biome-ignore lint/a11y/noNoninteractiveTabindex: the frame stands in for the glasses; keys are the gestures
        tabIndex={0}
        onKeyDown={onKey}
      >
        {card}
      </div>
      <fieldset className="lens-sim">
        <legend className="sr-only">Simulated gestures</legend>
        <button type="button" className="btn btn-primary" onClick={() => gesture("tap")}>
          Tap
        </button>
        <button type="button" className="btn" onClick={() => gesture("next")}>
          Swipe next
        </button>
        <button type="button" className="btn" onClick={() => gesture("back")}>
          Swipe back
        </button>
        <button type="button" className="btn btn-ghost" onClick={signOut}>
          Sign out
        </button>
        <span className="small">
          Keys: Enter or Space taps, the arrow keys swipe. Decisions are made on your phone.
        </span>
      </fieldset>
    </main>
  );
}
