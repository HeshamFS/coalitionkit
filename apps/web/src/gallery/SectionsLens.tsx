// SPDX-License-Identifier: Apache-2.0
import { LensCard, LensFrame } from "../components/lens";
import { Cell } from "./Cell";

const tapNext = [
  { gesture: "Tap" as const, does: "got it" },
  { gesture: "Swipe" as const, does: "next", tone: "muted" as const },
];
const yesNo = [
  { gesture: "Tap" as const, does: "yes" },
  { gesture: "Swipe" as const, does: "no", tone: "muted" as const },
];

/** The lens door, drawn at its real 600 x 600 size: one card, one step, black is transparent. */
export function Lens() {
  return (
    <>
      <div className="fam" data-testid="gallery-lens">
        <span className="fam-n">09b</span>
        <span className="fam-t">Glasses · lens door</span>
        <span className="fam-line" />
      </div>
      <div className="g2">
        <Cell
          name="LensCard"
          doors={["lens"]}
          props="title (22 px or more) · eyebrow? · body? (one line) · gestures: 0 to 2 · states: shown, acknowledged · min text 20 px at 600 px, no scroll, no hover"
          events="gesture(name): tap confirms, swipe moves on; a decision always has one more confirm step"
        >
          <div className="caps">Real size · 600 × 600 · step 1 of 3</div>
          <LensFrame label="Lens frame, information step">
            <LensCard
              eyebrow="Gather"
              title="Goal 1"
              body="3 members"
              step={{ index: 0, total: 3 }}
              hints={tapNext}
            />
          </LensFrame>
        </Cell>
        <Cell
          name="LensCard · ask"
          doors={["lens"]}
          props="the same card for a request: tap says yes, swipe says no, then a confirm step"
          events="lens.confirm(subject) · lens.next · lens.dismiss"
        >
          <div className="caps">Step 3 of 3 · asks you</div>
          <LensFrame label="Lens frame, request step">
            <LensCard
              eyebrow="Asks you · 1 of 1"
              title="Take Plan A?"
              body="Plan"
              step={{ index: 2, total: 3 }}
              hints={yesNo}
            />
          </LensFrame>
        </Cell>
        <Cell
          name="LensCard · confirm"
          doors={["lens"]}
          props="the confirm step: nothing is sent on the first tap"
          events="tap sends, swipe cancels"
        >
          <div className="caps">Confirm step</div>
          <LensFrame label="Lens frame, confirm step">
            <LensCard
              eyebrow="Confirm"
              title="Send yes?"
              body="Take Plan A?"
              hints={[
                { gesture: "Tap", does: "send" },
                { gesture: "Swipe", does: "cancel", tone: "muted" },
              ]}
            />
          </LensFrame>
        </Cell>
        <Cell
          name="LensCard · acknowledged"
          doors={["lens"]}
          props="state acknowledged: the answer was sent"
          events="tap closes"
        >
          <div className="caps">Acknowledged</div>
          <LensFrame label="Lens frame, acknowledged step">
            <LensCard
              state="acknowledged"
              eyebrow="Asks you · 1 of 1"
              title="Answer sent"
              hints={[{ gesture: "Tap", does: "close" }]}
            />
          </LensFrame>
        </Cell>
      </div>
    </>
  );
}
