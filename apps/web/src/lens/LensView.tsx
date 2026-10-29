// SPDX-License-Identifier: Apache-2.0
import { type KeyboardEvent, type ReactNode, useEffect, useMemo, useRef, useState } from "react";
import { LensCard, type LensGesture } from "../components/lens";
import { answerFor } from "../feed/actions";
import { useAgentSnapshot, useFeedApi, useFeedSnapshot } from "../feed/useFeed";
import { buildSteps, type Gesture, type LensStep, press, START } from "./machine";

/** The catalog components the lens draws. Every one of them has `lens` among its doors. */
export const LENS_COMPONENTS = ["LensCard"] as const;

function hintsFor(step: LensStep | undefined): LensGesture[] {
  if (step?.kind === "ask") {
    return [
      { gesture: "Tap", does: "yes" },
      { gesture: "Swipe", does: "no", tone: "muted" },
    ];
  }
  return [
    { gesture: "Tap", does: "got it" },
    { gesture: "Swipe", does: "next", tone: "muted" },
  ];
}

/**
 * The lens door (glasses simulator): one card, one step, 600 x 600. It reads the same feed as
 * the room and answers a request only through the host's answers endpoint, after a confirm step.
 */
export function LensView() {
  const feed = useFeedSnapshot();
  const agent = useAgentSnapshot();
  const { answer, agent: agentStore, signOut } = useFeedApi();
  const [machine, setMachine] = useState(START);
  const [sent, setSent] = useState<ReadonlySet<string>>(new Set());
  const frame = useRef<HTMLDivElement>(null);

  const steps = useMemo(
    () => buildSteps(feed.state, agent.requests, sent),
    [feed.state, agent.requests, sent],
  );
  const index = Math.max(0, Math.min(machine.index, steps.length - 1));
  const step = steps[index];

  useEffect(() => frame.current?.focus(), []);

  const gesture = (g: Gesture) => {
    if (agent.refusal) {
      agentStore.setRefusal(null);
      return;
    }
    const result = press(machine, steps, g);
    setMachine(result.state);
    if (!result.send) return;
    const { request, consent } = result.send;
    let body: ReturnType<typeof answerFor>;
    try {
      body = answerFor(request, consent);
    } catch {
      return;
    }
    void answer(body).then(() => {
      if (agentStore.getSnapshot().refusal === null) setSent((s) => new Set(s).add(request.id));
    });
  };

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

  let card: ReactNode;
  if (agent.refusal) {
    card = (
      <LensCard
        eyebrow="The host"
        title="Not taken"
        body={agent.refusal}
        hints={[{ gesture: "Tap", does: "close" }]}
      />
    );
  } else if (!step || (feed.state === null && feed.status === "connecting")) {
    card = <LensCard eyebrow="Coalition" title="Connecting" />;
  } else if (machine.ack !== null) {
    card = (
      <LensCard
        state="acknowledged"
        eyebrow={step.eyebrow}
        title={machine.ack}
        hints={[{ gesture: "Tap", does: "close" }]}
      />
    );
  } else if (machine.confirming && step.kind === "ask") {
    card = (
      <LensCard
        eyebrow="Confirm"
        title={machine.confirming.consent ? "Send yes?" : "Send no?"}
        body={step.title}
        hints={[
          { gesture: "Tap", does: "send" },
          { gesture: "Swipe", does: "cancel", tone: "muted" },
        ]}
      />
    );
  } else {
    card = (
      <LensCard
        eyebrow={step.eyebrow}
        title={step.title}
        body={step.body}
        step={{ index, total: steps.length }}
        hints={hintsFor(step)}
      />
    );
  }

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
          Keys: Enter or Space taps, the arrow keys swipe. A decision is always confirmed once more.
        </span>
      </fieldset>
    </main>
  );
}
