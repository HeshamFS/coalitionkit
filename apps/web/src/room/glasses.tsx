// SPDX-License-Identifier: Apache-2.0
// `/glasses` (story J-14): the viewer's current step only, one card, one step.
import { deriveSchedule } from "../feed/derive";
import { useAgentSnapshot, useFeedSnapshot } from "../feed/useFeed";
import { GlassesPage } from "../moments/GlassesPage";

export function GlassesRoute() {
  const feed = useFeedSnapshot();
  const agent = useAgentSnapshot();
  const steps = deriveSchedule(feed.state);
  const ask = agent.requests[0];
  if (ask) {
    return (
      <GlassesPage
        step={1}
        total={1}
        instruction="Your yes is needed"
        detail="Open your phone to read it and press and hold to sign"
        glyph="!"
      />
    );
  }
  const step = steps[0];
  if (!step) {
    return (
      <GlassesPage
        step={0}
        total={0}
        instruction="Nothing to do now"
        detail="Your agent is on it"
      />
    );
  }
  return (
    <GlassesPage
      step={1}
      total={steps.length}
      instruction={step.title}
      detail={step.time || undefined}
    />
  );
}
